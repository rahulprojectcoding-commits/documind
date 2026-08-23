from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from .forms import DocumentUploadForm, QuestionForm, SignUpForm
from .models import Document, OTPCode
from .tasks import process_document_task
from .retrieval import get_relevant_chunks
from .llm import answer_question
from .otp import generate_and_send_otp


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
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            document = Document.objects.create(file=form.cleaned_data["document"], owner=request.user)
            process_document_task.delay(document.id)
            return redirect("ask", document_id=document.id)
    else:
        form = DocumentUploadForm()

    documents = Document.objects.filter(owner=request.user).order_by("-uploaded_at")
    return render(request, "qa/upload.html", {"form": form, "documents": documents})


@login_required
def ask_view(request, document_id):
    document = get_object_or_404(Document, id=document_id, owner=request.user)
    answer = None
    error = None

    if request.method == "POST":
        form = QuestionForm(request.POST)
        if form.is_valid():
            question = form.cleaned_data["question"]
            chunks = get_relevant_chunks(document, question)
            context_text = "\n\n".join(chunk.text for chunk in chunks)
            answer = answer_question(context_text, question)
    else:
        form = QuestionForm()

    context = {"form": form, "answer": answer, "error": error, "document": document}

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


def document_status_partial(request, document_id):
    document = get_object_or_404(Document, id=document_id, owner=request.user)

    if document.status == "ready":
        form = QuestionForm()
        return render(request, "qa/partials/ready.html", {"document": document, "form": form})

    return render(request, "qa/partials/processing.html", {"document": document})