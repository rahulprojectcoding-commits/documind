from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from .models import OTPCode

OTP_VALID_MINUTES = 10


def generate_and_send_otp(user, purpose, channel="email"):
    code = OTPCode.generate_code()
    expires_at = timezone.now() + timedelta(minutes=OTP_VALID_MINUTES)

    OTPCode.objects.create(
        user=user,
        code=code,
        purpose=purpose,
        channel=channel,
        expires_at=expires_at,
    )

    if channel == "email":
        send_mail(
            "Your DocuMind verification code",
            f"Your verification code is: {code}\n\nIt expires in {OTP_VALID_MINUTES} minutes.",
            None,
            [user.email],
        )

    return code