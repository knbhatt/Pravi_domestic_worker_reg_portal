"""Serializers for ID card views."""

from rest_framework import serializers

from .models import WorkerIDCard


class WorkerIDCardSerializer(serializers.ModelSerializer):
    """Full ID card detail."""

    class Meta:
        model = WorkerIDCard
        fields = [
            "card_number",
            "pdf_s3_url",
            "issued_at",
            "valid_until",
        ]
        read_only_fields = fields


class IDCardVerifySerializer(serializers.Serializer):
    """Public QR scan verification response."""

    card_number = serializers.CharField()
    worker_name = serializers.CharField()
    work_type = serializers.CharField()
    issued_date = serializers.DateTimeField()
    valid_until = serializers.DateField()
    status = serializers.CharField()