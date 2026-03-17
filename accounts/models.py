from datetime import timedelta

from django.db import models
from django.utils import timezone


class OTPRecord(models.Model):
    """Stores OTP codes issued to a phone number."""

    phone_number = models.CharField(max_length=10)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["phone_number", "-created_at"]),
        ]

    def __str__(self) -> str:
        """Return human-readable representation."""
        return f"OTP for {self.phone_number} at {self.created_at.isoformat()}"

    @classmethod
    def create_new_otp(cls, phone_number: str, otp_code: str) -> "OTPRecord":
        """Create a new OTP and invalidate previous unused OTPs for the phone number."""
        now = timezone.now()
        cls.objects.filter(phone_number=phone_number, is_used=False, expires_at__gt=now).update(
            is_used=True
        )
        expires_at = now + timedelta(minutes=5)
        return cls.objects.create(
            phone_number=phone_number,
            otp_code=otp_code,
            expires_at=expires_at,
        )

    def is_expired(self) -> bool:
        """Return True if the OTP is expired."""
        return timezone.now() > self.expires_at

