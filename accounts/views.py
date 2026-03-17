"""Views for OTP-based authentication and JWT issuance."""

import logging
import random

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTTokenRefreshView

from workers.models import Worker
from .models import OTPRecord
from .serializers import OTPRequestSerializer, OTPVerifySerializer
from notifications.sms import send_otp_sms

logger = logging.getLogger(__name__)


def get_tokens_for_worker(worker: Worker) -> dict:
    """Create JWT refresh and access tokens for the given worker."""
    refresh = RefreshToken()
    refresh["worker_id"] = str(worker.id)
    refresh["phone_number"] = worker.phone_number
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


class OTPRequestView(APIView):
    """Handle OTP request for login."""

    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request, *args, **kwargs):
        """Validate phone number, create OTP, and send SMS."""
        serializer = OTPRequestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.info("OTP request validation error: %s", serializer.errors)
            return Response(
                {"success": False, "message": "Invalid data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone_number = serializer.validated_data["phone_number"]
        otp_code = f"{random.randint(0, 999999):06d}"

        try:
            otp = OTPRecord.create_new_otp(phone_number, otp_code)
            logger.info("Created OTP id=%s for phone=%s", otp.id, phone_number)
            send_otp_sms(phone_number, otp_code)
            Worker.objects.get_or_create(phone_number=phone_number)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error while generating OTP: %s", exc)
            return Response(
                {"success": False, "message": "Could not send OTP at this time."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_data = {
            "success": True,
            "message": "OTP sent successfully",
        }
        if getattr(settings, "DEBUG", False):
            response_data["debug_otp"] = otp_code
        return Response(response_data, status=status.HTTP_200_OK)


class OTPVerifyView(APIView):
    """Verify OTP and issue JWT tokens."""

    authentication_classes: list = []
    permission_classes: list = []

    def post(self, request, *args, **kwargs):
        """Validate OTP against the latest unused record and return JWT tokens."""
        serializer = OTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            logger.info("OTP verify validation error: %s", serializer.errors)
            return Response(
                {"success": False, "message": "Invalid data", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone_number = serializer.validated_data["phone_number"]
        otp_code = serializer.validated_data["otp_code"]

        now = timezone.now()
        otp = (
            OTPRecord.objects.filter(
                phone_number=phone_number,
                is_used=False,
                expires_at__gt=now,
            )
            .order_by("-created_at")
            .first()
        )

        if not otp:
            logger.info("OTP expired or not found for %s", phone_number)
            return Response(
                {"success": False, "message": "OTP expired or not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Increment attempts
        otp.attempts += 1

        if otp.attempts >= 3:
            otp.is_used = True
            otp.save(update_fields=["attempts", "is_used"])
            logger.info("Too many attempts for phone %s", phone_number)
            return Response(
                {"success": False, "message": "Too many attempts"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if otp.otp_code != otp_code:
            otp.save(update_fields=["attempts"])
            logger.info("Invalid OTP for phone %s", phone_number)
            return Response(
                {"success": False, "message": "Invalid OTP"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        otp.is_used = True
        otp.save(update_fields=["attempts", "is_used"])

        try:
            worker = Worker.objects.get(phone_number=phone_number)
        except Worker.DoesNotExist:
            logger.error("Worker not found for phone after OTP verify: %s", phone_number)
            return Response(
                {"success": False, "message": "Worker not found"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        tokens = get_tokens_for_worker(worker)
        data = {
            "access": tokens["access"],
            "refresh": tokens["refresh"],
            "worker_id": str(worker.id),
            "is_profile_complete": worker.is_profile_complete,
        }
        return Response(
            {"success": True, "message": "OTP verified successfully", "data": data},
            status=status.HTTP_200_OK,
        )


class TokenRefreshView(SimpleJWTTokenRefreshView):
    """Proxy to SimpleJWT refresh endpoint with unified response format."""

    def post(self, request, *args, **kwargs):
        """Return a refreshed access token."""
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            return Response(
                {"success": True, "message": "Token refreshed", "data": response.data},
                status=status.HTTP_200_OK,
            )
        return Response(
            {"success": False, "message": "Could not refresh token", "errors": response.data},
            status=response.status_code,
        )


class LogoutView(APIView):
    """Logout by blacklisting the refresh token."""

    def post(self, request, *args, **kwargs):
        """Blacklist the provided refresh token if possible."""
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {
                    "success": False,
                    "message": "Refresh token is required.",
                    "errors": {"refresh": ["This field is required."]},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error while blacklisting refresh token: %s", exc)
            return Response(
                {"success": False, "message": "Could not logout."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {"success": True, "message": "Logged out successfully", "data": {}},
            status=status.HTTP_200_OK,
        )

