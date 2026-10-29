from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from qa.models import OTPCode


class MobileAuthenticationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="mobile-reader",
            email="reader@example.com",
            password="StrongPass123!",
        )

    @patch("qa.api_views.generate_and_send_otp")
    def test_password_login_sends_otp_but_does_not_issue_token(self, send_otp):
        response = self.client.post(
            reverse("api_mobile_login"),
            {"username": "mobile-reader", "password": "StrongPass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["username"], self.user.username)
        send_otp.assert_called_once_with(self.user, purpose="login", channel="email")
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    @patch("qa.api_views.generate_and_send_otp")
    def test_invalid_password_does_not_send_otp(self, send_otp):
        response = self.client.post(
            reverse("api_mobile_login"),
            {"username": "mobile-reader", "password": "wrong"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        send_otp.assert_not_called()

    def test_valid_otp_issues_token_once(self):
        otp = OTPCode.objects.create(
            user=self.user,
            code="123456",
            purpose="login",
            channel="email",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        response = self.client.post(
            reverse("api_mobile_verify_otp"),
            {"username": "mobile-reader", "code": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["token"], self.user.auth_token.key)
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)

    def test_expired_otp_does_not_issue_token(self):
        OTPCode.objects.create(
            user=self.user,
            code="123456",
            purpose="login",
            channel="email",
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        response = self.client.post(
            reverse("api_mobile_verify_otp"),
            {"username": "mobile-reader", "code": "123456"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_five_incorrect_codes_lock_the_otp(self):
        otp = OTPCode.objects.create(
            user=self.user,
            code="123456",
            purpose="login",
            channel="email",
            expires_at=timezone.now() + timedelta(minutes=5),
        )

        for _ in range(5):
            response = self.client.post(
                reverse("api_mobile_verify_otp"),
                {"username": "mobile-reader", "code": "000000"},
                format="json",
            )
            self.assertEqual(response.status_code, 400)

        otp.refresh_from_db()
        self.assertEqual(otp.attempts, 5)
        self.assertTrue(otp.is_used)
        response = self.client.post(
            reverse("api_mobile_verify_otp"),
            {"username": "mobile-reader", "code": "123456"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_legacy_password_only_token_endpoint_is_removed(self):
        response = self.client.post("/api/token/", {
            "username": "mobile-reader",
            "password": "StrongPass123!",
        })

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

    def test_authenticated_user_can_logout_and_revoke_token(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.post(reverse("api_mobile_logout"), format="json")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Token.objects.filter(user=self.user).exists())

