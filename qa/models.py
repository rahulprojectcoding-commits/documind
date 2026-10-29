from django.db import models
from pgvector.django import VectorField
from django.conf import settings
import secrets
from django.utils import timezone
from datetime import timedelta


class Collection(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="document_collections",
    )
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "name"],
                name="unique_collection_name_per_owner",
            )
        ]

    def __str__(self):
        return self.name


class Document(models.Model):
    STATUS_CHOICES = [
        ("processing", "Processing"),
        ("ready", "Ready"),
        ("failed", "Failed"),
    ]
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="documents/")
    display_name = models.CharField(max_length=255, blank=True)
    collection = models.ForeignKey(
        Collection,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="documents",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="processing")
    processing_error = models.TextField(blank=True)

    @property
    def title(self):
        return self.display_name or self.file.name.rsplit("/", 1)[-1]

    def __str__(self):
        return self.file.name


class Chunk(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="chunks")
    text = models.TextField()
    embedding = VectorField(dimensions=768)
    order = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.document} chunk {self.order}"


class AnswerRecord(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="answer_history",
    )
    document = models.ForeignKey(
        Document,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="answer_history",
    )
    collection = models.ForeignKey(
        Collection,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="answer_history",
    )
    question = models.TextField()
    answer = models.TextField()
    sources = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.question[:80]} ({self.created_at:%Y-%m-%d})"


class AnswerFeedback(models.Model):
    RATING_CHOICES = [
        ("helpful", "Helpful"),
        ("not_helpful", "Not helpful"),
    ]
    answer = models.ForeignKey(
        AnswerRecord,
        on_delete=models.CASCADE,
        related_name="feedback",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="answer_feedback",
    )
    rating = models.CharField(max_length=20, choices=RATING_CHOICES)
    comment = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["answer", "owner"],
                name="unique_answer_feedback_per_user",
            )
        ]

    def __str__(self):
        return f"{self.rating} feedback for answer {self.answer_id}"



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
    attempts = models.PositiveSmallIntegerField(default=0)

    def __str__(self):
        return f"{self.purpose} OTP for {self.user} via {self.channel}"

    @staticmethod
    def generate_code():
        return f"{secrets.randbelow(1000000):06d}"

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
