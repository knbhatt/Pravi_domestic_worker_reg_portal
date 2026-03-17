from django.contrib import admin

from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin configuration for worker documents."""

    list_display = ("worker", "doc_type", "uploaded_at", "is_verified")
    list_filter = ("doc_type", "is_verified", "uploaded_at")
    search_fields = ("worker__full_name", "worker__phone_number")

