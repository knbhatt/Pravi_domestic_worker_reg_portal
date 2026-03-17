"""Views for worker personal and work profiles."""

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsWorker
from applications.models import Application
from documents.models import Document
from .models import WorkerProfile
from .serializers import WorkerDetailSerializer, WorkerProfileSerializer, WorkerSerializer

logger = logging.getLogger(__name__)


class WorkerMeView(APIView):
    """Return the authenticated worker's complete profile."""

    permission_classes = [IsWorker]

    def get(self, request, *args, **kwargs):
        """Return combined worker, profile, document, and application status data."""
        worker = request.worker
        try:
            profile = WorkerProfile.objects.filter(worker=worker).first()
            docs = Document.objects.filter(worker=worker)
            documents_status = {
                "aadhaar": docs.filter(doc_type="aadhaar").exists(),
                "photo": docs.filter(doc_type="photo").exists(),
            }
            app = Application.objects.filter(worker=worker).first()
            data = {
                "worker": WorkerSerializer(worker).data,
                "profile": WorkerProfileSerializer(profile).data if profile else None,
                "documents": documents_status,
                "application_status": app.status if app else None,
            }
            serializer = WorkerDetailSerializer(data)
            return Response(
                {"success": True, "message": "Worker profile fetched", "data": serializer.data},
                status=status.HTTP_200_OK,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error fetching worker profile: %s", exc)
            return Response(
                {"success": False, "message": "Could not fetch worker profile."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class WorkerProfileView(APIView):
    """Create or update worker personal details."""

    permission_classes = [IsWorker]

    def post(self, request, *args, **kwargs):
        """Update the current worker's personal details."""
        worker = request.worker
        serializer = WorkerSerializer(instance=worker, data=request.data, partial=True)
        if not serializer.is_valid():
            logger.info("Worker profile validation error: %s", serializer.errors)
            return Response(
                {"success": False, "message": "Invalid data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            worker = serializer.save()
            required_fields = [worker.full_name, worker.date_of_birth, worker.gender, worker.address]
            worker.is_profile_complete = all(required_fields)
            worker.save(update_fields=["full_name", "date_of_birth", "gender", "address", "city", "state", "pincode", "is_profile_complete"])
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error updating worker profile: %s", exc)
            return Response(
                {"success": False, "message": "Could not update profile."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "message": "Profile updated successfully",
                "data": WorkerSerializer(worker).data,
            },
            status=status.HTTP_200_OK,
        )


class WorkerWorkDetailsView(APIView):
    """Create or update worker work profile details."""

    permission_classes = [IsWorker]

    def post(self, request, *args, **kwargs):
        """Create or update the worker's work profile."""
        worker = request.worker
        profile, _ = WorkerProfile.objects.get_or_create(worker=worker)
        serializer = WorkerProfileSerializer(instance=profile, data=request.data, partial=True)
        if not serializer.is_valid():
            logger.info("Worker work details validation error: %s", serializer.errors)
            return Response(
                {"success": False, "message": "Invalid data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            profile = serializer.save()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error updating worker work details: %s", exc)
            return Response(
                {"success": False, "message": "Could not update work details."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "message": "Work details updated successfully",
                "data": WorkerProfileSerializer(profile).data,
            },
            status=status.HTTP_200_OK,
        )

