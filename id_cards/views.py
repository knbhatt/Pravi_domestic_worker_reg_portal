"""Views for ID card download and public QR verification."""

import logging

from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsWorker
from .models import WorkerIDCard
from .serializers import WorkerIDCardSerializer

logger = logging.getLogger(__name__)


class IDCardDownloadView(APIView):
    """Return the worker's ID card PDF URL."""

    permission_classes = [IsWorker]

    def get(self, request, *args, **kwargs):
        worker = request.worker
        try:
            app = worker.application
            id_card = app.workeridcard
            return Response(
                {
                    "success": True,
                    "message": "ID card fetched.",
                    "data": WorkerIDCardSerializer(id_card).data,
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            return Response(
                {"success": False, "message": "ID card not available yet."},
                status=status.HTTP_404_NOT_FOUND,
            )


class IDCardVerifyView(APIView):
    """Public endpoint for QR code verification."""

    authentication_classes = []
    permission_classes = []

    def get(self, request, card_number, *args, **kwargs):
        try:
            card = WorkerIDCard.objects.select_related(
                "application__worker__workerprofile"
            ).get(card_number=card_number)

            today = timezone.now().date()
            card_status = "valid" if card.valid_until >= today else "expired"

            try:
                work_type = card.application.worker.workerprofile.get_work_type_display()
            except Exception:
                work_type = "N/A"

            data = {
                "card_number": card.card_number,
                "worker_name": card.application.worker.full_name,
                "work_type": work_type,
                "issued_date": card.issued_at,
                "valid_until": card.valid_until,
                "status": card_status,
            }
            return Response(
                {"success": True, "message": "Card verified.", "data": data},
                status=status.HTTP_200_OK,
            )
        except WorkerIDCard.DoesNotExist:
            return Response(
                {"success": False, "message": "Card not found."},
                status=status.HTTP_404_NOT_FOUND,
            )