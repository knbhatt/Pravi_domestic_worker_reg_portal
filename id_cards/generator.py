"""PDF ID card generator using ReportLab."""

import io
import json
import logging
import os
import tempfile

import qrcode
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A6, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

NAVY = colors.HexColor("#1a3a5c")
WHITE = colors.white
LIGHT_GRAY = colors.HexColor("#f5f5f5")


def _generate_qr_image(data: str) -> str:
    """Generate QR code and return temp file path."""
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name)
    tmp.close()
    return tmp.name


def generate_worker_id_card(worker, application, card_number: str):
    """
    Generate PDF ID card. Returns (pdf_s3_key, pdf_s3_url, valid_until, qr_data).
    Saves locally if S3 not configured.
    """
    from id_cards.models import WorkerIDCard
    valid_until = WorkerIDCard.calculate_valid_until()

    buffer = io.BytesIO()
    page_width, page_height = landscape(A6)
    c = canvas.Canvas(buffer, pagesize=landscape(A6))

    # Header
    c.setFillColor(NAVY)
    c.rect(0, page_height - 28*mm, page_width, 28*mm, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(page_width/2, page_height - 10*mm,
                        "DOMESTIC WORKER REGISTRATION")
    c.setFont("Helvetica", 8)
    c.drawCentredString(page_width/2, page_height - 18*mm,
                        "Government of Gujarat — Labour Department")

    # Body background
    c.setFillColor(LIGHT_GRAY)
    c.rect(0, 0, page_width, page_height - 28*mm, fill=1, stroke=0)

    # Worker details
    detail_x = 12*mm
    detail_y = page_height - 36*mm
    line_gap = 6.5*mm

    fields = [
        ("Name", worker.full_name or "N/A"),
        ("Card No", card_number),
        ("Phone", worker.phone_number[:5] + "XXXXX"),
        ("Valid Until", valid_until.strftime("%d %b %Y")),
        ("Ref ID", application.reference_id),
    ]

    try:
        profile = worker.workerprofile
        fields.insert(2, ("Work Type", profile.get_work_type_display()))
    except Exception:
        pass

    for label, value in fields:
        c.setFillColor(NAVY)
        c.setFont("Helvetica-Bold", 8)
        c.drawString(detail_x, detail_y, f"{label}:")
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8)
        c.drawString(detail_x + 22*mm, detail_y, str(value))
        detail_y -= line_gap

    # QR code
    verify_url = f"http://127.0.0.1:8000/api/id-card/verify/{card_number}/"
    qr_data = json.dumps({
        "card_number": card_number,
        "name": worker.full_name,
        "valid_until": valid_until.isoformat(),
        "verify_url": verify_url,
    })

    try:
        qr_path = _generate_qr_image(qr_data)
        c.drawImage(qr_path, page_width - 30*mm, 4*mm,
                    width=26*mm, height=26*mm)
        os.unlink(qr_path)
    except Exception as e:
        logger.warning("QR generation failed: %s", e)

    # Footer
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 6)
    c.drawString(detail_x, 8*mm, "Scan QR code to verify authenticity")
    c.drawString(detail_x, 4*mm, "Issued by: Labour Dept, Gujarat")

    c.save()

    # Save PDF — locally if no S3
    bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
    aws_key = getattr(settings, 'AWS_ACCESS_KEY_ID', '')
    s3_key = f"id_cards/{worker.id}/{card_number}.pdf"

    if bucket and aws_key and not aws_key.startswith("your_"):
        # Upload to S3
        try:
            import boto3
            client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
            buffer.seek(0)
            client.upload_fileobj(
                buffer, bucket, s3_key,
                ExtraArgs={"ContentType": "application/pdf"}
            )
            s3_url = (f"https://{bucket}.s3."
                      f"{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_key}")
        except Exception as e:
            logger.exception("S3 upload failed: %s", e)
            s3_url = _save_locally(buffer, card_number)
    else:
        s3_url = _save_locally(buffer, card_number)

    return s3_key, s3_url, valid_until, qr_data


def _save_locally(buffer, card_number: str) -> str:
    """Save PDF to local media folder and return URL."""
    import os
    from django.conf import settings

    media_dir = os.path.join(settings.MEDIA_ROOT, "id_cards")
    os.makedirs(media_dir, exist_ok=True)
    filename = f"{card_number}.pdf"
    filepath = os.path.join(media_dir, filename)

    buffer.seek(0)
    with open(filepath, 'wb') as f:
        f.write(buffer.read())

    return f"/media/id_cards/{filename}"