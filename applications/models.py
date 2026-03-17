import uuid
from datetime import datetime
from random import randint

from django.conf import settings
from django.db import models
from django.utils import timezone

from workers.models import Worker


STATUS_CHOICES = [
    ("draft", "Draft"),
    ("submitted", "Submitted"),
    ("under_review", "Under Review"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]


class Application(models.Model):
    """Represents a worker's registration application."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    worker = models.OneToOneField(Worker, on_delete=models.CASCADE)
    reference_id = models.CharField(max_length=20, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        """Return human-readable identifier."""
        return f"{self.reference_id or 'UNASSIGNED'} ({self.worker})"

    @staticmethod
    def generate_reference_id() -> str:
        """Generate a new reference ID with format DWR-YYYY-XXXXXX."""
        year = datetime.now().year
        number = randint(0, 999_999)
        return f"DWR-{year}-{number:06d}"

    def set_submitted(self) -> None:
        """Mark application as submitted and assign reference ID if needed."""
        self.status = "submitted"
        self.submitted_at = timezone.now()
        if not self.reference_id:
            self.reference_id = self.generate_reference_id()

