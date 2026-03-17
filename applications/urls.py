from django.urls import path

from .views import ApplicationStatusView, ApplicationSubmitView

urlpatterns = [
    path("submit/", ApplicationSubmitView.as_view(), name="application-submit"),
    path("status/", ApplicationStatusView.as_view(), name="application-status"),
]