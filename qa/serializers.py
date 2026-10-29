from pathlib import PurePosixPath
from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "id",
            "file",
            "display_name",
            "collection",
            "status",
            "processing_error",
            "uploaded_at",
        ]
        read_only_fields = ["id", "status", "processing_error", "uploaded_at"]

    def validate_file(self, uploaded_file):
        extension = PurePosixPath(uploaded_file.name).suffix.lower()
        if extension not in {".pdf", ".txt"}:
            raise serializers.ValidationError("Upload a PDF or TXT file.")
        if uploaded_file.size > 25 * 1024 * 1024:
            raise serializers.ValidationError("Files must be 25 MB or smaller.")
        return uploaded_file

    def validate_collection(self, collection):
        request = self.context.get("request")
        if collection and request and collection.owner_id != request.user.id:
            raise serializers.ValidationError("Choose one of your own collections.")
        return collection


class QuestionSerializer(serializers.Serializer):
    question = serializers.CharField()
