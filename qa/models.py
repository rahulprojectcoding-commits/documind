from django.db import models
from pgvector.django import VectorField
from django.conf import settings
import secrets
from django.utils import timezone
from datetime import timedelta


class Document(models.Model):
    STATUS_CHOICES = [
        ("processing", "Processing"),
        ("ready", "Ready"),
        ("failed", "Failed"),
    ]
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="processing")


    def __str__(self):
        return self.file.name


class Chunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    text = models.TextField()
    embedding = VectorField(dimensions=768)
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.document} chunk {self.order}"



class OTPCode(models.Model):
    PURPOSE_CHOICES = [
        ("signup", "Signup verification"),
        ("login", "Login verification"),
    ]
    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="otp_codes")
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=10, choices=PURPOSE_CHOICES)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.purpose} OTP for {self.user} via {self.channel}"

    @staticmethod
    def generate_code():
        return f"{secrets.randbelow(1000000):06d}"

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at