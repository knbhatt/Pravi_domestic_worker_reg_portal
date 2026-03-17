from django.urls import path

from .views import WorkerMeView, WorkerProfileView, WorkerWorkDetailsView

urlpatterns = [
    path("me/", WorkerMeView.as_view(), name="workers-me"),
    path("profile/", WorkerProfileView.as_view(), name="workers-profile"),
    path("work-details/", WorkerWorkDetailsView.as_view(), name="workers-work-details"),
]
