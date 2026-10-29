import logging

from django.db.models import CharField, Count, Q, Value
from django.db.models.functions import Coalesce, Lower, NullIf
from django.http import HttpResponseNotAllowed, JsonResponse
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.views.decorators.http import require_GET

from .forms import (
    CollectionForm,
    DocumentManageForm,
    DocumentUploadForm,
    QuestionForm,
    SignUpForm,
)
from .models import AnswerFeedback, AnswerRecord, Collection, Document, OTPCode
from .tasks import process_document_task
from .otp import generate_and_send_otp
from .services import answer_for_documents

logger = logging.getLogger(__name__)


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            generate_and_send_otp(user, purpose="login", channel="email")
            request.session["pending_verification_user_id"] = user.id
            request.session["pending_verification_purpose"] = "login"
            return redirect("verify_otp")
    else:
        form = AuthenticationForm()

    return render(request, "qa/login.html", {"form": form})


@login_required
def upload_view(request):
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            document = Document.objects.create(
                file=form.cleaned_data["document"],
                owner=request.user,
                collection=form.cleaned_data["collection"],
            )
            try:
                process_document_task.delay(document.id)
            except Exception:
                logger.exception("Could not queue document %s", document.id)
                document.status = "failed"
                document.processing_error = "The document could not be queued. Please retry."
                document.save(update_fields=["status", "processing_error"])
            if document.collection_id:
                return redirect("collection_ask", collection_id=document.collection_id)
            return redirect("ask", document_id=document.id)
    else:
        form = DocumentUploadForm(user=request.user)

    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "")
    collection_filter = request.GET.get("collection", "")
    sort = request.GET.get("sort", "newest")
    documents = Document.objects.filter(owner=request.user).select_related("collection")
    if query:
        documents = documents.filter(
            Q(display_name__icontains=query) | Q(file__icontains=query)
        )
    if status_filter in {"processing", "ready", "failed"}:
        documents = documents.filter(status=status_filter)
    if collection_filter:
        documents = documents.filter(
            collection_id=collection_filter,
            collection__owner=request.user,
        )
    if sort == "oldest":
        documents = documents.order_by("uploaded_at")
    elif sort == "name":
        documents = documents.annotate(
            sort_name=Lower(
                Coalesce(
                    NullIf("display_name", Value("")),
                    "file",
                    output_field=CharField(),
                )
            )
        ).order_by("sort_name")
    else:
        sort = "newest"
        documents = documents.order_by("-uploaded_at")

    collections = Collection.objects.filter(owner=request.user).annotate(
        document_count=Count("documents"),
        ready_count=Count("documents", filter=Q(documents__status="ready")),
    )
    return render(request, "qa/upload.html", {
        "form": form,
        "documents": documents,
        "collections": collections,
        "collection_form": CollectionForm(user=request.user),
        "query": query,
        "status_filter": status_filter,
        "collection_filter": collection_filter,
        "sort": sort,
    })


@login_required
def ask_view(request, document_id):
    document = get_object_or_404(Document, id=document_id, owner=request.user)
    answer = None
    error = None
    sources = []
    answer_record = None

    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid() and document.status == "ready":
            question = form.cleaned_data["question"]
            try:
                answer, sources, answer_record = answer_for_documents(
                    owner=request.user,
                    question=question,
                    documents=[document],
                    document=document,
                )
            except Exception:
                logger.exception("Answer generation failed for document %s", document.id)
                error = "We couldn’t answer that right now. Please try again."
        elif document.status != "ready":
            error = "This document isn’t ready yet. Try again when processing finishes."
    else:
        form = QuestionForm()

    context = {
        "form": form,
        "answer": answer,
        "answer_record": answer_record,
        "sources": sources,
        "error": error,
        "document": document,
        "history": document.answer_history.filter(owner=request.user).prefetch_related("feedback")[:10],
    }

    if request.headers.get("HX-Request") == "true":
        return render(request, "qa/partials/ready.html", context)

    return render(request, "qa/ask.html", context)




def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            generate_and_send_otp(user, purpose="signup", channel="email")
            request.session["pending_verification_user_id"] = user.id
            request.session["pending_verification_purpose"] = "signup"
            return redirect("verify_otp")
    else:
        form = SignUpForm()

    return render(request, "qa/signup.html", {"form": form})


def verify_otp_view(request):
    user_id = request.session.get("pending_verification_user_id")
    purpose = request.session.get("pending_verification_purpose", "signup")

    if not user_id:
        return redirect("signup")

    user = get_object_or_404(User, id=user_id)
    error = None

    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        otp = OTPCode.objects.filter(
            user=user, purpose=purpose, code=code
        ).order_by("-created_at").first()

        if otp and otp.is_valid():
            otp.is_used = True
            otp.save()

            if purpose == "signup":
                user.is_active = True
                user.save()

            login(request, user)
            del request.session["pending_verification_user_id"]
            request.session.pop("pending_verification_purpose", None)
            return redirect("upload")
        else:
            error = "Invalid or expired code."

    return render(request, "qa/verify_otp.html", {"error": error})


@login_required
def document_status_partial(request, document_id):
    document = get_object_or_404(Document, id=document_id, owner=request.user)

    if document.status == "ready":
        form = QuestionForm()
        return render(request, "qa/partials/ready.html", {
            "document": document,
            "form": form,
            "sources": [],
            "answer": None,
            "history": document.answer_history.filter(owner=request.user)[:10],
        })
    if document.status == "failed":
        return render(request, "qa/partials/failed.html", {"document": document})

    return render(request, "qa/partials/processing.html", {"document": document})



@login_required
def delete_document_view(request, document_id):
    document = get_object_or_404(Document, id=document_id, owner=request.user)
    if request.method == "POST":
        document.file.delete(save=False)
        document.delete()
    return redirect("upload")


@login_required
def create_collection_view(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    form = CollectionForm(request.POST, user=request.user)
    if form.is_valid():
        collection = form.save(commit=False)
        collection.owner = request.user
        collection.save()
        messages.success(request, f'Collection “{collection.name}” created.')
    else:
        messages.error(request, form.errors.as_text())
    return redirect("upload")


@login_required
def collection_ask_view(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id, owner=request.user)
    documents = collection.documents.filter(owner=request.user)
    ready_documents = list(documents.filter(status="ready"))
    answer = error = answer_record = None
    sources = []
    form = QuestionForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        if not ready_documents:
            error = "This collection has no processed documents to search yet."
        else:
            try:
                answer, sources, answer_record = answer_for_documents(
                    owner=request.user,
                    question=form.cleaned_data["question"],
                    documents=ready_documents,
                    collection=collection,
                )
            except Exception:
                logger.exception("Answer generation failed for collection %s", collection.id)
                error = "We couldn’t answer that right now. Please try again."

    context = {
        "collection": collection,
        "documents": documents,
        "ready_documents": ready_documents,
        "form": form,
        "answer": answer,
        "answer_record": answer_record,
        "sources": sources,
        "error": error,
        "history": collection.answer_history.filter(owner=request.user).prefetch_related("feedback")[:20],
    }
    return render(request, "qa/collection_ask.html", context)


@login_required
def manage_document_view(request, document_id):
    document = get_object_or_404(Document, id=document_id, owner=request.user)
    form = DocumentManageForm(
        request.POST or None,
        instance=document,
        user=request.user,
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("upload")
    return render(request, "qa/manage_document.html", {"document": document, "form": form})


@login_required
def retry_document_view(request, document_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    document = get_object_or_404(Document, id=document_id, owner=request.user)
    if document.status == "failed":
        document.chunks.all().delete()
        document.status = "processing"
        document.processing_error = ""
        document.save(update_fields=["status", "processing_error"])
        try:
            process_document_task.delay(document.id)
        except Exception:
            logger.exception("Could not queue retry for document %s", document.id)
            document.status = "failed"
            document.processing_error = "The document could not be queued. Please retry."
            document.save(update_fields=["status", "processing_error"])
    return redirect("upload")


@login_required
def history_view(request):
    history = AnswerRecord.objects.filter(owner=request.user).select_related(
        "document", "collection"
    ).prefetch_related("feedback")[:100]
    return render(request, "qa/history.html", {"history": history})


@login_required
def profile_view(request):
    documents = Document.objects.filter(owner=request.user)
    return render(request, "qa/profile.html", {
        "document_count": documents.count(),
        "ready_count": documents.filter(status="ready").count(),
        "processing_count": documents.filter(status="processing").count(),
        "failed_count": documents.filter(status="failed").count(),
    })


@login_required
def feedback_view(request, answer_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    answer = get_object_or_404(AnswerRecord, id=answer_id, owner=request.user)
    rating = request.POST.get("rating")
    if rating in {"helpful", "not_helpful"}:
        AnswerFeedback.objects.update_or_create(
            answer=answer,
            owner=request.user,
            defaults={
                "rating": rating,
                "comment": request.POST.get("comment", "").strip()[:500],
            },
        )
    if answer.document_id:
        return redirect("ask", document_id=answer.document_id)
    if answer.collection_id:
        return redirect("collection_ask", collection_id=answer.collection_id)
    return redirect("history")


@require_GET
def health_check(request):
    from django.db import connection
    from django.db.utils import DatabaseError

    try:
        connection.ensure_connection()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
