import uuid

from django.db import models


class Worker(models.Model):
    """Represents a domestic worker using the system."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=10, unique=True)
    full_name = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=(
            ("M", "Male"),
            ("F", "Female"),
            ("Other", "Other"),
        ),
    )
    address = models.TextField(blank=True)
    city = models.CharField(max_length=50, blank=True)
    state = models.CharField(max_length=50, blank=True)
    pincode = models.CharField(max_length=6, blank=True)
    is_profile_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """Return worker display name."""
        return f"{self.full_name or 'Unnamed'} ({self.phone_number})"


WORK_TYPE_CHOICES = [
    ("maid", "Maid / Housekeeping"),
    ("cook", "Cook"),
    ("driver", "Driver"),
    ("gardener", "Gardener"),
    ("security", "Security Guard"),
    ("childcare", "Child Care"),
    ("eldercare", "Elder Care"),
    ("other", "Other"),
]


class WorkerProfile(models.Model):
    """Detailed work profile for a worker."""

    worker = models.OneToOneField(Worker, on_delete=models.CASCADE)
    work_type = models.CharField(max_length=20, choices=WORK_TYPE_CHOICES)
    other_work_type = models.CharField(max_length=50, blank=True)
    years_experience = models.IntegerField(default=0)
    languages_known = models.CharField(max_length=200)
    availability = models.CharField(
        max_length=20,
        choices=(
            ("full_time", "Full Time"),
            ("part_time", "Part Time"),
            ("live_in", "Live-in"),
        ),
    )
    preferred_area = models.CharField(max_length=100, blank=True)
    expected_salary = models.IntegerField(null=True, blank=True)

    def __str__(self) -> str:
        """Return a human-readable description of the profile."""
        return f"Profile for {self.worker}"

