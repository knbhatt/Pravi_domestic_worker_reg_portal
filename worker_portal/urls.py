from django.urls import path
from . import views

urlpatterns = [
    path("", views.home_view, name="home"),        # ← add this
    path("login/", views.login_view, name="worker-login"),
    path("otp/", views.otp_view, name="worker-otp"),
    path("dashboard/", views.dashboard_view, name="worker-dashboard"),
    path("profile/", views.profile_view, name="worker-profile"),
    path("work-details/", views.work_details_view, name="worker-work-details"),
    path("documents/", views.documents_view, name="worker-documents"),
    path("upload/aadhaar/", views.upload_aadhaar_view, name="worker-upload-aadhaar"),
    path("upload/photo/", views.upload_photo_view, name="worker-upload-photo"),
    path("submit/", views.submit_application_view, name="worker-submit"),
    path("logout/", views.logout_view, name="worker-logout"),
    path("id-card/", views.id_card_view, name="worker-id-card"),
]