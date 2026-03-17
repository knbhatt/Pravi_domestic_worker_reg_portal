"""Celery task for generating worker ID cards after approval."""

import logging

from celery import shared_task

from notifications.tasks import send_approval_sms

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_id_card(self, application_id: str) -> None:
    """Generate PDF ID card for an approved application."""
    try:
        from applications.models import Application
        from id_cards.models import WorkerIDCard
        from id_cards.generator import generate_worker_id_card

        app = Application.objects.get(id=application_id)
        worker = app.worker

        card_number = WorkerIDCard.generate_card_number()
        s3_key, s3_url, valid_until, qr_data = generate_worker_id_card(
            worker, app, card_number
        )

        id_card, _ = WorkerIDCard.objects.update_or_create(
            application=app,
            defaults={
                "card_number": card_number,
                "qr_code_data": qr_data,
                "pdf_s3_key": s3_key,
                "pdf_s3_url": s3_url,
                "valid_until": valid_until,
            },
        )

        logger.info("ID card %s generated for worker %s", card_number, worker.phone_number)
        send_approval_sms.delay(worker.phone_number, s3_url)

    except Exception as exc:
        logger.exception("Error generating ID card for application %s: %s", application_id, exc)
        raise self.retry(exc=exc)