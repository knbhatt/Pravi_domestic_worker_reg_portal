import uuid

from django.db import models

from workers.models import Worker


DOC_TYPE_CHOICES = [
    ("aadhaar", "Aadhaar Card"),
    ("photo", "Profile Photo"),
]


class Document(models.Model):
    """Represents a document uploaded by a worker and stored on S3."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    s3_key = models.CharField(max_length=500)
    s3_url = models.CharField(max_length=1000)
    file_size = models.IntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)

    class Meta:
        unique_together = ["worker", "doc_type"]

    def __str__(self) -> str:
        """Return human-readable description."""
        return f"{self.doc_type} for {self.worker}"

