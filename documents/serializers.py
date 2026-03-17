"""Serializers for worker document uploads and listing."""

from rest_framework import serializers

from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    """Read-only representation of a worker document."""

    class Meta:
        model = Document
        fields = ["id", "doc_type", "s3_url", "uploaded_at", "is_verified"]
        read_only_fields = fields


class DocumentUploadSerializer(serializers.Serializer):
    """Serializer for handling document file upload."""

    file = serializers.FileField()

