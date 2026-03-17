"""Views for uploading and listing worker documents stored on S3."""

import logging
import mimetypes
import time
from typing import Tuple

import boto3
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsWorker
from .models import Document
from .serializers import DocumentSerializer, DocumentUploadSerializer

logger = logging.getLogger(__name__)


def _get_s3_client():
    """Return a boto3 S3 client."""
    return boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )


def _upload_to_s3(file_obj, key: str) -> Tuple[str, str]:
    """Upload the given file object to S3 at the provided key."""
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    client = _get_s3_client()
    content_type, _ = mimetypes.guess_type(file_obj.name)
    extra_args = {"ContentType": content_type or "application/octet-stream"}
    client.upload_fileobj(file_obj, bucket, key, ExtraArgs=extra_args)
    s3_url = f"https://{bucket}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{key}"
    return key, s3_url


class AadhaarUploadView(APIView):
    """Upload Aadhaar document for the worker."""

    permission_classes = [IsWorker]

    def post(self, request, *args, **kwargs):
        """Handle Aadhaar document upload with validation and S3 storage."""
        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            logger.info("Aadhaar upload validation error: %s", serializer.errors)
            return Response(
                {"success": False, "message": "Invalid data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        worker = request.worker
        file_obj = serializer.validated_data["file"]
        filename = file_obj.name.lower()
        size = file_obj.size

        if not (filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png") or filename.endswith(".pdf")):
            return Response(
                {
                    "success": False,
                    "message": "Unsupported file type for Aadhaar.",
                    "errors": {"file": ["Allowed types: jpg, jpeg, png, pdf."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if size > 5 * 1024 * 1024:
            return Response(
                {
                    "success": False,
                    "message": "File too large.",
                    "errors": {"file": ["Max size is 5MB for Aadhaar."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            timestamp = int(time.time())
            key = f"documents/{worker.id}/aadhaar/{timestamp}_{file_obj.name}"
            s3_key, s3_url = _upload_to_s3(file_obj, key)
            doc, _ = Document.objects.update_or_create(
                worker=worker,
                doc_type="aadhaar",
                defaults={"s3_key": s3_key, "s3_url": s3_url, "file_size": size},
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error uploading Aadhaar to S3: %s", exc)
            return Response(
                {"success": False, "message": "Could not upload Aadhaar."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "message": "Aadhaar uploaded successfully",
                "data": DocumentSerializer(doc).data,
            },
            status=status.HTTP_201_CREATED,
        )


class PhotoUploadView(APIView):
    """Upload profile photo for the worker."""

    permission_classes = [IsWorker]

    def post(self, request, *args, **kwargs):
        """Handle profile photo upload with validation and S3 storage."""
        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            logger.info("Photo upload validation error: %s", serializer.errors)
            return Response(
                {"success": False, "message": "Invalid data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        worker = request.worker
        file_obj = serializer.validated_data["file"]
        filename = file_obj.name.lower()
        size = file_obj.size

        if not (filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png")):
            return Response(
                {
                    "success": False,
                    "message": "Unsupported file type for photo.",
                    "errors": {"file": ["Allowed types: jpg, jpeg, png."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if size > 2 * 1024 * 1024:
            return Response(
                {
                    "success": False,
                    "message": "File too large.",
                    "errors": {"file": ["Max size is 2MB for photo."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            timestamp = int(time.time())
            key = f"documents/{worker.id}/photo/{timestamp}_{file_obj.name}"
            s3_key, s3_url = _upload_to_s3(file_obj, key)
            doc, _ = Document.objects.update_or_create(
                worker=worker,
                doc_type="photo",
                defaults={"s3_key": s3_key, "s3_url": s3_url, "file_size": size},
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error uploading photo to S3: %s", exc)
            return Response(
                {"success": False, "message": "Could not upload photo."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "success": True,
                "message": "Photo uploaded successfully",
                "data": DocumentSerializer(doc).data,
            },
            status=status.HTTP_201_CREATED,
        )


class DocumentListView(APIView):
    """List documents uploaded by the authenticated worker."""

    permission_classes = [IsWorker]

    def get(self, request, *args, **kwargs):
        """Return a list of documents for the worker."""
        worker = request.worker
        try:
            docs = Document.objects.filter(worker=worker).order_by("doc_type", "-uploaded_at")
            data = DocumentSerializer(docs, many=True).data
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error listing documents: %s", exc)
            return Response(
                {"success": False, "message": "Could not fetch documents."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"success": True, "message": "Documents fetched", "data": data},
            status=status.HTTP_200_OK,
        )

