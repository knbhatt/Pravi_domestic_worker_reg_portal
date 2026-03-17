import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone

from applications.models import Application


class WorkerIDCard(models.Model):
    """Represents an issued digital ID card for a worker."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(Application, on_delete=models.CASCADE)
    card_number = models.CharField(max_length=20, unique=True)
    qr_code_data = models.CharField(max_length=500)
    pdf_s3_key = models.CharField(max_length=500)
    pdf_s3_url = models.CharField(max_length=1000)
    issued_at = models.DateTimeField(auto_now_add=True)
    valid_until = models.DateField()

    def __str__(self) -> str:
        """Return card identifier."""
        return f"{self.card_number}"

    @staticmethod
    def generate_card_number() -> str:
        """Generate card number in the format DWID-YYYY-XXXXXXXX."""
        now = timezone.now()
        year = now.year
        from random import randint

        number = randint(0, 99_999_999)
        return f"DWID-{year}-{number:08d}"

    @staticmethod
    def calculate_valid_until(issued_at: timezone.datetime | None = None):
        """Return date three years from issue date."""
        issued = issued_at or timezone.now()
        return (issued + timedelta(days=3 * 365)).date()

