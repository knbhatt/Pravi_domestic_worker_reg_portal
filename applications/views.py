"""Views for application submit, status, and officer actions."""

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsOfficer, IsWorker
from documents.models import Document
from notifications.tasks import send_submission_sms
from workers.models import WorkerProfile
from .models import Application
from .serializers import ApplicationSerializer, ApplicationStatusSerializer

logger = logging.getLogger(__name__)


class ApplicationSubmitView(APIView):
    """Submit a worker's registration application."""

    permission_classes = [IsWorker]

    def post(self, request, *args, **kwargs):
        worker = request.worker

        # Check personal details
        missing = []
        if not worker.full_name:
            missing.append("full_name")
        if not worker.date_of_birth:
            missing.append("date_of_birth")
        if not worker.gender:
            missing.append("gender")
        if not worker.address:
            missing.append("address")
        if missing:
            return Response(
                {
                    "success": False,
                    "message": "Incomplete profile.",
                    "errors": {f: ["This field is required."] for f in missing},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check work profile
        if not WorkerProfile.objects.filter(worker=worker).exists():
            return Response(
                {"success": False, "message": "Work details are required before submitting."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check documents
        docs = Document.objects.filter(worker=worker)
        if not docs.filter(doc_type="aadhaar").exists():
            return Response(
                {"success": False, "message": "Aadhaar document is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not docs.filter(doc_type="photo").exists():
            return Response(
                {"success": False, "message": "Profile photo is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            app, created = Application.objects.get_or_create(worker=worker)
            if app.status in ("approved",):
                return Response(
                    {"success": False, "message": "Application already approved."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            app.set_submitted()
            app.save()
            send_submission_sms.delay(worker.phone_number, app.reference_id)
            logger.info("Application %s submitted for worker %s", app.reference_id, worker.phone_number)
        except Exception as exc:
            logger.exception("Error submitting application: %s", exc)
            return Response(
                {"success": False, "message": "Could not submit application."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "message": "Application submitted successfully.",
                "data": ApplicationSerializer(app).data,
            },
            status=status.HTTP_201_CREATED,
        )


class ApplicationStatusView(APIView):
    """Check application status for the authenticated worker."""

    permission_classes = [IsWorker]

    def get(self, request, *args, **kwargs):
        worker = request.worker
        try:
            app = Application.objects.filter(worker=worker).first()
            if not app:
                return Response(
                    {"success": False, "message": "No application found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            id_card_url = None
            if app.status == "approved":
                try:
                    id_card_url = app.workeridcard.pdf_s3_url
                except Exception:
                    pass

            data = {
                "reference_id": app.reference_id,
                "status": app.status,
                "id_card_url": id_card_url,
                "rejection_reason": app.rejection_reason or None,
            }
            return Response(
                {"success": True, "message": "Status fetched.", "data": data},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("Error fetching application status: %s", exc)
            return Response(
                {"success": False, "message": "Could not fetch status."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )