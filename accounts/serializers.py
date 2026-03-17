"""Serializers for OTP-based worker authentication."""

import re

from rest_framework import serializers


PHONE_REGEX = re.compile(r"^[6-9]\d{9}$")
OTP_REGEX = re.compile(r"^\d{6}$")


class OTPRequestSerializer(serializers.Serializer):
    """Validate phone number for OTP request."""

    phone_number = serializers.CharField(max_length=10)

    def validate_phone_number(self, value: str) -> str:
        """Ensure the phone number is a valid Indian mobile number."""
        if not PHONE_REGEX.match(value):
            raise serializers.ValidationError("Enter a valid 10-digit Indian mobile number.")
        return value


class OTPVerifySerializer(serializers.Serializer):
    """Validate phone number and OTP code for verification."""

    phone_number = serializers.CharField(max_length=10)
    otp_code = serializers.CharField(max_length=6)

    def validate_phone_number(self, value: str) -> str:
        """Validate phone number field."""
        if not PHONE_REGEX.match(value):
            raise serializers.ValidationError("Enter a valid 10-digit Indian mobile number.")
        return value

    def validate_otp_code(self, value: str) -> str:
        """Validate OTP format."""
        if not OTP_REGEX.match(value):
            raise serializers.ValidationError("OTP must be a 6-digit numeric code.")
        return value

