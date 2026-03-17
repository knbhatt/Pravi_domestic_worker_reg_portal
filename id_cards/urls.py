from django.urls import path

from .views import IDCardDownloadView, IDCardVerifyView

urlpatterns = [
    path("download/", IDCardDownloadView.as_view(), name="id-card-download"),
    path("verify/<str:card_number>/", IDCardVerifyView.as_view(), name="id-card-verify"),
]