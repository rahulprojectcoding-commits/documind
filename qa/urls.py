from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from . import views
from . import api_views

urlpatterns = [
    path("", views.upload_view, name="upload"),
    path("login/", views.login_view, name="login"),
    path("health/", views.health_check, name="health_check"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="qa/password_reset_form.html",
            email_template_name="qa/password_reset_email.html",
            subject_template_name="qa/password_reset_subject.txt",
            success_url=reverse_lazy("password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="qa/password_reset_done.html",
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="qa/password_reset_confirm.html",
            success_url=reverse_lazy("password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="qa/password_reset_complete.html",
        ),
        name="password_reset_complete",
    ),
    path("ask/<int:document_id>/", views.ask_view, name="ask"),
    path("collections/create/", views.create_collection_view, name="create_collection"),
    path("collections/<int:collection_id>/ask/", views.collection_ask_view, name="collection_ask"),
    path("signup/", views.signup_view, name="signup"),
    path("ask/<int:document_id>/status/", views.document_status_partial, name="document_status"),
    path("documents/<int:document_id>/manage/", views.manage_document_view, name="manage_document"),
    path("documents/<int:document_id>/retry/", views.retry_document_view, name="retry_document"),
    path("history/", views.history_view, name="history"),
    path("profile/", views.profile_view, name="profile"),
    path("answers/<int:answer_id>/feedback/", views.feedback_view, name="answer_feedback"),
    path("api/documents/", api_views.DocumentListCreateView.as_view(), name="api_document_list"),
    path("api/documents/<int:pk>/", api_views.DocumentDetailView.as_view(), name="api_document_detail"),
    path("api/documents/<int:document_id>/ask/", api_views.AskAPIView.as_view(), name="api_ask"),
    path("api/collections/<int:collection_id>/ask/", api_views.AskCollectionAPIView.as_view(), name="api_collection_ask"),
    path("verify/", views.verify_otp_view, name="verify_otp"),
    path("documents/<int:document_id>/delete/", views.delete_document_view, name="delete_document"),
]
