"""Serializers for worker applications."""

from rest_framework import serializers

from .models import Application


class ApplicationSerializer(serializers.ModelSerializer):
    """Lightweight serializer for application status."""

    class Meta:
        model = Application
        fields = [
            "id",
            "reference_id",
            "status",
            "submitted_at",
            "reviewed_at",
            "rejection_reason",
        ]
        read_only_fields = fields


class ApplicationStatusSerializer(serializers.Serializer):
    """Serializer for status check response including ID card URL."""

    reference_id = serializers.CharField()
    status = serializers.CharField()
    id_card_url = serializers.CharField(allow_null=True)
    rejection_reason = serializers.CharField(allow_null=True)


class RejectSerializer(serializers.Serializer):
    """Serializer for rejection reason."""

    reason = serializers.CharField(min_length=10)