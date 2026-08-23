from django.urls import path
from . import views
from . import api_views

urlpatterns = [
    path("", views.upload_view, name="upload"),
    path("login/", views.login_view, name="login"),
    path("ask/<int:document_id>/", views.ask_view, name="ask"),
    path("signup/", views.signup_view, name="signup"),
    path("ask/<int:document_id>/status/", views.document_status_partial, name="document_status"),
    path("api/documents/", api_views.DocumentListCreateView.as_view(), name="api_document_list"),
    path("api/documents/<int:pk>/", api_views.DocumentDetailView.as_view(), name="api_document_detail"),
    path("api/documents/<int:document_id>/ask/", api_views.AskAPIView.as_view(), name="api_ask"),
    path("verify/", views.verify_otp_view, name="verify_otp"),
]