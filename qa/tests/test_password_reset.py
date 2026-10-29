from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="old-password-123",
        )

    @patch("django.contrib.auth.forms.PasswordResetForm.send_mail")
    def test_request_sends_reset_email_and_uses_generic_confirmation(self, send_mail):
        response = self.client.post(
            reverse("password_reset"),
            {"email": self.user.email},
        )

        self.assertRedirects(response, reverse("password_reset_done"))
        send_mail.assert_called_once()

    @patch("django.contrib.auth.forms.PasswordResetForm.send_mail")
    def test_unknown_email_gets_same_confirmation_without_sending_mail(self, send_mail):
        response = self.client.post(
            reverse("password_reset"),
            {"email": "unknown@example.com"},
        )

        self.assertRedirects(response, reverse("password_reset_done"))
        send_mail.assert_not_called()

    def test_valid_reset_link_changes_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        reset_url = reverse(
            "password_reset_confirm",
            kwargs={"uidb64": uid, "token": token},
        )

        response = self.client.get(reset_url, follow=True)
        self.assertTemplateUsed(response, "qa/password_reset_confirm.html")
        self.assertTrue(response.context["validlink"])

        response = self.client.post(
            response.wsgi_request.path,
            {
                "new_password1": "A-very-strong-new-password-914",
                "new_password2": "A-very-strong-new-password-914",
            },
        )

        self.assertRedirects(response, reverse("password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("A-very-strong-new-password-914"))

    def test_invalid_reset_link_is_rejected(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        response = self.client.get(
            reverse(
                "password_reset_confirm",
                kwargs={"uidb64": uid, "token": "invalid-token"},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["validlink"])
