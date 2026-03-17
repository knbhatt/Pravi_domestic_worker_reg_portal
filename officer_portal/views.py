"""Officer portal API views for application management."""

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsOfficer
from applications.models import Application
from applications.serializers import ApplicationSerializer, RejectSerializer
from id_cards.tasks import generate_id_card
from notifications.tasks import send_rejection_sms

logger = logging.getLogger(__name__)


class OfficerApplicationListView(APIView):
    """List all applications with optional filters."""

    permission_classes = [IsOfficer]

    def get(self, request, *args, **kwargs):
        qs = Application.objects.select_related("worker").all().order_by("-submitted_at")

        app_status = request.query_params.get("status")
        if app_status:
            qs = qs.filter(status=app_status)

        city = request.query_params.get("city")
        if city:
            qs = qs.filter(worker__city__icontains=city)

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(
                reference_id__icontains=search
            ) | qs.filter(
                worker__full_name__icontains=search
            ) | qs.filter(
                worker__phone_number__icontains=search
            )

        data = ApplicationSerializer(qs, many=True).data
        return Response(
            {"success": True, "message": "Applications fetched.", "data": data},
            status=status.HTTP_200_OK,
        )


class OfficerApplicationDetailView(APIView):
    """Get full detail of a single application."""

    permission_classes = [IsOfficer]

    def get(self, request, pk, *args, **kwargs):
        try:
            app = Application.objects.select_related(
                "worker__workerprofile"
            ).get(id=pk)
            data = ApplicationSerializer(app).data
            return Response(
                {"success": True, "message": "Application fetched.", "data": data},
                status=status.HTTP_200_OK,
            )
        except Application.DoesNotExist:
            return Response(
                {"success": False, "message": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )


class OfficerApproveView(APIView):
    """Approve a single application."""

    permission_classes = [IsOfficer]

    def post(self, request, pk, *args, **kwargs):
        try:
            app = Application.objects.get(id=pk)
        except Application.DoesNotExist:
            return Response(
                {"success": False, "message": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if app.status == "approved":
            return Response(
                {"success": False, "message": "Already approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        app.status = "approved"
        app.reviewed_by = request.user
        app.reviewed_at = timezone.now()
        app.save()
        generate_id_card.delay(str(app.id))
        logger.info("Application %s approved by %s", app.reference_id, request.user)

        return Response(
            {"success": True, "message": "Application approved. ID card is being generated."},
            status=status.HTTP_200_OK,
        )


class OfficerRejectView(APIView):
    """Reject a single application with a reason."""

    permission_classes = [IsOfficer]

    def post(self, request, pk, *args, **kwargs):
        serializer = RejectSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "message": "Reason is required.", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            app = Application.objects.get(id=pk)
        except Application.DoesNotExist:
            return Response(
                {"success": False, "message": "Application not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        app.status = "rejected"
        app.reviewed_by = request.user
        app.reviewed_at = timezone.now()
        app.rejection_reason = serializer.validated_data["reason"]
        app.save()
        send_rejection_sms.delay(app.worker.phone_number, app.rejection_reason)
        logger.info("Application %s rejected by %s", app.reference_id, request.user)

        return Response(
            {"success": True, "message": "Application rejected."},
            status=status.HTTP_200_OK,
        )


class OfficerDashboardStatsView(APIView):
    """Return summary stats for the officer dashboard."""

    permission_classes = [IsOfficer]

    def get(self, request, *args, **kwargs):
        today = timezone.now().date()
        data = {
            "total": Application.objects.count(),
            "submitted": Application.objects.filter(status="submitted").count(),
            "under_review": Application.objects.filter(status="under_review").count(),
            "approved": Application.objects.filter(status="approved").count(),
            "rejected": Application.objects.filter(status="rejected").count(),
            "today_submissions": Application.objects.filter(
                submitted_at__date=today
            ).count(),
        }
        return Response(
            {"success": True, "message": "Stats fetched.", "data": data},
            status=status.HTTP_200_OK,
        )