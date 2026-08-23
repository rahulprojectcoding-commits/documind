from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Document
from .serializers import DocumentSerializer, QuestionSerializer
from .tasks import process_document_task
from .retrieval import get_relevant_chunks
from .llm import answer_question


class DocumentListCreateView(generics.ListCreateAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(owner=self.request.user).order_by("-uploaded_at")

    def perform_create(self, serializer):
        document = serializer.save(owner=self.request.user)
        process_document_task.delay(document.id)


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

        chunks = get_relevant_chunks(document, question)
        context_text = "\n\n".join(chunk.text for chunk in chunks)
        answer = answer_question(context_text, question)

        return Response({"question": question, "answer": answer})