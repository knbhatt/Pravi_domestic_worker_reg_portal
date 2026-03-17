from django.contrib import admin

from .models import OTPRecord


@admin.register(OTPRecord)
class OTPRecordAdmin(admin.ModelAdmin):
    """Admin configuration for OTP records."""

    list_display = ("phone_number", "otp_code", "created_at", "expires_at", "is_used", "attempts")
    list_filter = ("is_used", "created_at")
    search_fields = ("phone_number", "otp_code")

