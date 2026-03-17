from django.urls import path

from .views import AadhaarUploadView, DocumentListView, PhotoUploadView

urlpatterns = [
    path("upload/aadhaar/", AadhaarUploadView.as_view(), name="documents-upload-aadhaar"),
    path("upload/photo/", PhotoUploadView.as_view(), name="documents-upload-photo"),
    path("list/", DocumentListView.as_view(), name="documents-list"),
]
