from django.contrib import admin

from .models import Worker, WorkerProfile


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    """Admin for worker basic information."""

    list_display = ("phone_number", "full_name", "city", "state", "is_profile_complete", "created_at")
    search_fields = ("phone_number", "full_name", "city", "state")
    list_filter = ("city", "state", "is_profile_complete")


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    """Admin for worker profile details."""

    list_display = ("worker", "work_type", "years_experience", "availability")
    search_fields = ("worker__full_name", "worker__phone_number", "preferred_area")
    list_filter = ("work_type", "availability")

