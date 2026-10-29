import logging

from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Document
from .serializers import DocumentSerializer, QuestionSerializer
from .tasks import process_document_task
from .models import Collection
from .services import answer_for_documents

logger = logging.getLogger(__name__)


class DocumentListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user).order_by("-uploaded_at")

    def perform_create(self, serializer):
        document = serializer.save(owner=self.request.user)
        try:
            process_document_task.delay(document.id)
        except Exception:
            logger.exception("Could not queue API upload %s", document.id)
            document.status = "failed"
            document.processing_error = "The document could not be queued. Please retry."
            document.save(update_fields=["status", "processing_error"])


class DocumentDetailView(generics.RetrieveAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user)


class AskAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, document_id):
        document = generics.get_object_or_404(
            Document, id=document_id, owner=request.user
        )

        if document.status != "ready":
            return Response({"error": "Document is not ready yet"}, status=409)

        serializer = QuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.validated_data["question"]

        try:
            answer, sources, record = answer_for_documents(
                owner=request.user,
                question=question,
                documents=[document],
                document=document,
            )
        except Exception:
            logger.exception("API answer generation failed for document %s", document.id)
            return Response(
                {"error": "We couldn’t answer that right now. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response({
            "question": question,
            "answer": answer,
            "sources": sources,
            "answer_id": record.id,
        })


class AskCollectionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, collection_id):
        collection = generics.get_object_or_404(
            Collection,
            id=collection_id,
            owner=request.user,
        )
        documents = list(
            collection.documents.filter(owner=request.user, status="ready")
        )
        if not documents:
            return Response(
                {"error": "Collection has no processed documents yet."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = QuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        question = serializer.validated_data["question"]
        try:
            answer, sources, record = answer_for_documents(
                owner=request.user,
                question=question,
                documents=documents,
                collection=collection,
            )
        except Exception:
            logger.exception("API answer generation failed for collection %s", collection.id)
            return Response(
                {"error": "We couldn’t answer that right now. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({
            "question": question,
            "answer": answer,
            "sources": sources,
            "answer_id": record.id,
        })
