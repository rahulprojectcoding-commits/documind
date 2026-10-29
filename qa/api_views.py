import logging

from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from rest_framework import generics, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.throttling import ScopedRateThrottle
from .models import Document
from .serializers import DocumentSerializer, QuestionSerializer
from .tasks import process_document_task
from .models import Collection, OTPCode
from .otp import generate_and_send_otp
from .services import answer_for_documents

logger = logging.getLogger(__name__)
User = get_user_model()


class MobileLoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mobile_login"

    def post(self, request):
        username = str(request.data.get("username", "")).strip()
        password = request.data.get("password", "")
        user = authenticate(request, username=username, password=password)
        if not user or not user.is_active:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not user.email:
            return Response(
                {"detail": "This account has no email address for verification."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        OTPCode.objects.filter(
            user=user, purpose="login", is_used=False
        ).update(is_used=True)
        try:
            generate_and_send_otp(user, purpose="login", channel="email")
        except Exception:
            logger.exception("Could not send mobile login OTP for user %s", user.pk)
            return Response(
                {"detail": "Could not send a verification code. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"detail": "Verification code sent.", "username": user.get_username()})


class MobileVerifyOTPAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "mobile_verify_otp"

    def post(self, request):
        username = str(request.data.get("username", "")).strip()
        code = str(request.data.get("code", "")).strip()
        if len(code) != 6 or not code.isdigit():
            return Response({"detail": "Enter the six-digit verification code."}, status=400)

        user = User.objects.filter(username__iexact=username, is_active=True).first()
        with transaction.atomic():
            otp = None
            if user:
                otp = OTPCode.objects.select_for_update().filter(
                    user=user, purpose="login", channel="email", is_used=False
                ).order_by("-created_at").first()
            if not otp or not otp.is_valid() or otp.code != code:
                if otp and otp.is_valid():
                    otp.attempts += 1
                    if otp.attempts >= 5:
                        otp.is_used = True
                    otp.save(update_fields=["attempts", "is_used"])
                return Response({"detail": "Invalid or expired verification code."}, status=400)

            otp.is_used = True
            otp.save(update_fields=["is_used"])

        # Rotate any earlier mobile/API token after the second factor succeeds.
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        return Response({"token": token.key, "username": user.get_username()})


class MobileLogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MobileMeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "id": request.user.pk,
            "username": request.user.get_username(),
            "email": request.user.email,
        })


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
