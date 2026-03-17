from django.urls import path

from .views import (
    OfficerApplicationDetailView,
    OfficerApplicationListView,
    OfficerApproveView,
    OfficerDashboardStatsView,
    OfficerRejectView,
)

urlpatterns = [
    path("applications/", OfficerApplicationListView.as_view(), name="officer-applications"),
    path("applications/<str:pk>/", OfficerApplicationDetailView.as_view(), name="officer-application-detail"),
    path("applications/<str:pk>/approve/", OfficerApproveView.as_view(), name="officer-approve"),
    path("applications/<str:pk>/reject/", OfficerRejectView.as_view(), name="officer-reject"),
    path("dashboard/stats/", OfficerDashboardStatsView.as_view(), name="officer-stats"),
]