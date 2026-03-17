"""Customized Django Admin for government officer application review."""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from applications.models import Application
from documents.models import Document
from id_cards.tasks import generate_id_card
from notifications.tasks import send_rejection_sms
from workers.models import Worker, WorkerProfile


class DocumentInline(admin.TabularInline):
    """Show documents inline inside application detail."""

    model = Document
    fk_name = "worker"
    extra = 0
    readonly_fields = ["doc_type", "doc_preview", "uploaded_at", "is_verified"]
    fields = ["doc_type", "doc_preview", "uploaded_at", "is_verified"]
    can_delete = False

    def doc_preview(self, obj):
        if obj.s3_url:
            return format_html('<a href="{}" target="_blank">View Document</a>', obj.s3_url)
        return "No URL"
    doc_preview.short_description = "Preview"


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    """Main officer review interface for applications."""

    list_display = [
        "reference_id",
        "worker_name",
        "worker_phone",
        "work_type",
        "worker_city",
        "status",
        "submitted_at",
    ]
    list_filter = ["status", "submitted_at", "reviewed_at"]
    search_fields = [
        "reference_id",
        "worker__full_name",
        "worker__phone_number",
        "worker__city",
    ]
    readonly_fields = [
        "reference_id",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
        "worker_full_details",
    ]
    actions = ["approve_selected", "reject_selected"]
    inlines = []

    fieldsets = (
        ("Application Info", {
            "fields": ("reference_id", "status", "submitted_at", "reviewed_at", "reviewed_by")
        }),
        ("Worker Details", {
            "fields": ("worker_full_details",)
        }),
        ("Officer Notes", {
            "fields": ("notes", "rejection_reason")
        }),
    )

    def worker_name(self, obj):
        return obj.worker.full_name or "—"
    worker_name.short_description = "Name"

    def worker_phone(self, obj):
        return obj.worker.phone_number
    worker_phone.short_description = "Phone"

    def worker_city(self, obj):
        return obj.worker.city or "—"
    worker_city.short_description = "City"

    def work_type(self, obj):
        try:
            return obj.worker.workerprofile.get_work_type_display()
        except Exception:
            return "—"
    work_type.short_description = "Work Type"

    def worker_full_details(self, obj):
        """Render complete worker info inside the admin detail view."""
        w = obj.worker
        try:
            p = w.workerprofile
            profile_html = f"""
                <b>Work Type:</b> {p.get_work_type_display()}<br>
                <b>Experience:</b> {p.years_experience} years<br>
                <b>Languages:</b> {p.languages_known}<br>
                <b>Availability:</b> {p.get_availability_display()}<br>
            """
        except Exception:
            profile_html = "<i>No work profile</i>"

        return format_html("""
            <b>Name:</b> {}<br>
            <b>Phone:</b> {}<br>
            <b>DOB:</b> {}<br>
            <b>Gender:</b> {}<br>
            <b>Address:</b> {}, {}, {} - {}<br><br>
            {}
        """,
            w.full_name or "—",
            w.phone_number,
            w.date_of_birth or "—",
            w.gender or "—",
            w.address or "—", w.city or "—", w.state or "—", w.pincode or "—",
            format_html(profile_html),
        )
    worker_full_details.short_description = "Worker Information"

    @admin.action(description="Approve selected applications")
    def approve_selected(self, request, queryset):
        approved = 0
        for app in queryset.filter(status__in=["submitted", "under_review"]):
            app.status = "approved"
            app.reviewed_by = request.user
            app.reviewed_at = timezone.now()
            app.save()
            generate_id_card.delay(str(app.id))
            approved += 1
        self.message_user(request, f"{approved} application(s) approved. ID cards are being generated.")

    @admin.action(description="Reject selected applications")
    def reject_selected(self, request, queryset):
        rejected = 0
        for app in queryset.filter(status__in=["submitted", "under_review"]):
            app.status = "rejected"
            app.reviewed_by = request.user
            app.reviewed_at = timezone.now()
            app.rejection_reason = "Rejected by officer. Please check your documents and resubmit."
            app.save()
            send_rejection_sms.delay(app.worker.phone_number, app.rejection_reason)
            rejected += 1
        self.message_user(request, f"{rejected} application(s) rejected.")