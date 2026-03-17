"""Serializers for worker personal and work profile details."""

import datetime
import re

from django.utils import timezone
from rest_framework import serializers

from .models import WORK_TYPE_CHOICES, Worker, WorkerProfile


NAME_REGEX = re.compile(r"^[A-Za-z\s]{2,100}$")


class WorkerSerializer(serializers.ModelSerializer):
    """Serializer for worker core fields."""

    class Meta:
        model = Worker
        fields = [
            "id",
            "phone_number",
            "full_name",
            "date_of_birth",
            "gender",
            "address",
            "city",
            "state",
            "pincode",
            "is_profile_complete",
            "created_at",
        ]
        read_only_fields = ["id", "phone_number", "is_profile_complete", "created_at"]

    def validate_full_name(self, value: str) -> str:
        """Validate full name as alphabetic with spaces."""
        if value and not NAME_REGEX.match(value):
            raise serializers.ValidationError(
                "Full name must be 2-100 alphabetic characters without numbers or symbols."
            )
        return value

    def validate_date_of_birth(self, value: datetime.date | None) -> datetime.date | None:
        """Ensure DOB is between 18 and 70 years old and not in the future."""
        if not value:
            return value
        today = timezone.now().date()
        if value > today:
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if age < 18 or age > 70:
            raise serializers.ValidationError("Worker must be between 18 and 70 years old.")
        return value

    def validate_pincode(self, value: str) -> str:
        """Validate Indian pincode."""
        if value and (len(value) != 6 or not value.isdigit()):
            raise serializers.ValidationError("Pincode must be a 6-digit number.")
        return value


class WorkerProfileSerializer(serializers.ModelSerializer):
    """Serializer for worker work profile data."""

    class Meta:
        model = WorkerProfile
        fields = [
            "work_type",
            "other_work_type",
            "years_experience",
            "languages_known",
            "availability",
            "preferred_area",
            "expected_salary",
        ]

    def validate_years_experience(self, value: int) -> int:
        """Ensure non-negative experience."""
        if value < 0:
            raise serializers.ValidationError("Years of experience cannot be negative.")
        return value

    def validate(self, attrs):
        """Ensure other_work_type is filled when work_type is 'other'."""
        work_type = attrs.get("work_type", getattr(self.instance, "work_type", None))
        other = attrs.get("other_work_type", getattr(self.instance, "other_work_type", ""))
        if work_type == "other" and not other:
            raise serializers.ValidationError(
                {"other_work_type": "This field is required when work type is 'Other'."}
            )
        return attrs


class WorkerDetailSerializer(serializers.Serializer):
    """Aggregate worker, profile, and simple status information."""

    worker = WorkerSerializer()
    profile = WorkerProfileSerializer(allow_null=True)
    documents = serializers.DictField(child=serializers.BooleanField(), default=dict)
    application_status = serializers.CharField(allow_null=True)

