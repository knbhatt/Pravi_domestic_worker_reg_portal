from django.contrib import admin

from .models import WorkerIDCard


@admin.register(WorkerIDCard)
class WorkerIDCardAdmin(admin.ModelAdmin):
    """Admin configuration for worker ID cards."""

    list_display = ("card_number", "application", "issued_at", "valid_until")
    search_fields = ("card_number", "application__reference_id", "application__worker__phone_number")
    list_filter = ("issued_at",)

