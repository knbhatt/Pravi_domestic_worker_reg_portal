"""Celery tasks for SMS notifications."""

import logging

from celery import shared_task

from .sms import send_sms

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_submission_sms(self, phone_number: str, reference_id: str) -> None:
    """Send SMS when an application is submitted."""
    message = (
        f"Your domestic worker registration has been submitted. "
        f"Reference ID: {reference_id}. You will be notified once reviewed."
    )
    try:
        send_sms(phone_number, message)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send submission SMS, retrying: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_approval_sms(self, phone_number: str, card_download_url: str) -> None:
    """Send SMS when an application is approved."""
    message = (
        "Congratulations! Your registration is approved. "
        f"Download your ID card: {card_download_url}"
    )
    try:
        send_sms(phone_number, message)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send approval SMS, retrying: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_rejection_sms(self, phone_number: str, reason: str) -> None:
    """Send SMS when an application is rejected."""
    message = (
        "Your registration was not approved. "
        f"Reason: {reason}. Please login to resubmit."
    )
    try:
        send_sms(phone_number, message)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send rejection SMS, retrying: %s", exc)
        raise self.retry(exc=exc)

