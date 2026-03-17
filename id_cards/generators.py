"""PDF ID card generator using ReportLab and qrcode."""

import io
import json
import logging
import tempfile

import boto3
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


def _download_photo_from_s3(s3_key: str) -> str | None:
    """Download worker photo from S3 to a temp file, return path."""
    try:
        client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
        client.download_fileobj(settings.AWS_STORAGE_BUCKET_NAME, s3_key, tmp)
        tmp.close()
        return tmp.name
    except Exception as exc:
        logger.warning("Could not download worker photo: %s", exc)
        return None


def _generate_qr_image(data: str) -> str:
    """Generate QR code image and return temp file path."""
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name)
    tmp.close()
    return tmp.name


def _upload_pdf_to_s3(buffer: io.BytesIO, key: str) -> str:
    """Upload PDF buffer to S3 and return public URL."""
    client = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )
    buffer.seek(0)
    client.upload_fileobj(
        buffer,
        settings.AWS_STORAGE_BUCKET_NAME,
        key,
        ExtraArgs={"ContentType": "application/pdf"},
    )
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    region = settings.AWS_S3_REGION_NAME
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def generate_worker_id_card(worker, application, card_number: str) -> tuple[str, str]:
    """
    Generate a PDF ID card for the worker.
    Returns (pdf_s3_key, pdf_s3_url).
    """
    buffer = io.BytesIO()
    page_width, page_height = landscape(A6)
    c = canvas.Canvas(buffer, pagesize=landscape(A6))

    # Header background
    c.setFillColor(NAVY)
    c.rect(0, page_height - 30 * mm, page_width, 30 * mm, fill=1, stroke=0)

    # Header text
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(page_width / 2, page_height - 12 * mm, "DOMESTIC WORKER REGISTRATION")
    c.setFont("Helvetica", 9)
    c.drawCentredString(page_width / 2, page_height - 20 * mm, "Government of Gujarat — Labour Department")

    # Body background
    c.setFillColor(LIGHT_GRAY)
    c.rect(0, 0, page_width, page_height - 30 * mm, fill=1, stroke=0)

    # Worker photo
    photo_x = 8 * mm
    photo_y = page_height - 72 * mm
    photo_w = 28 * mm
    photo_h = 32 * mm

    try:
        photo_doc = worker.document_set.filter(doc_type="photo").first()
        if photo_doc:
            photo_path = _download_photo_from_s3(photo_doc.s3_key)
            if photo_path:
                c.drawImage(photo_path, photo_x, photo_y, width=photo_w, height=photo_h, preserveAspectRatio=True)
    except Exception as exc:
        logger.warning("Could not place photo on ID card: %s", exc)
        c.setFillColor(colors.lightgrey)
        c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=0)
        c.setFillColor(colors.grey)
        c.setFont("Helvetica", 7)
        c.drawCentredString(photo_x + photo_w / 2, photo_y + photo_h / 2, "PHOTO")

    # Worker details
    detail_x = 44 * mm
    detail_y = page_height - 38 * mm
    line_gap = 7 * mm

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(detail_x, detail_y, "Name:")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    c.drawString(detail_x + 22 * mm, detail_y, worker.full_name or "N/A")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(detail_x, detail_y - line_gap, "Card No:")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    c.drawString(detail_x + 22 * mm, detail_y - line_gap, card_number)

    try:
        profile = worker.workerprofile
        work_type_display = profile.get_work_type_display()
    except Exception:
        work_type_display = "N/A"

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(detail_x, detail_y - 2 * line_gap, "Work Type:")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    c.drawString(detail_x + 22 * mm, detail_y - 2 * line_gap, work_type_display)

    from id_cards.models import WorkerIDCard
    valid_until = WorkerIDCard.calculate_valid_until()
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(detail_x, detail_y - 3 * line_gap, "Valid Until:")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    c.drawString(detail_x + 22 * mm, detail_y - 3 * line_gap, valid_until.strftime("%d %b %Y"))

    masked_phone = worker.phone_number[:5] + "XXXXX"
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(detail_x, detail_y - 4 * line_gap, "Phone:")
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.black)
    c.drawString(detail_x + 22 * mm, detail_y - 4 * line_gap, masked_phone)

    # QR code
    verify_url = f"https://yourdomain.com/api/id-card/verify/{card_number}/"
    qr_data = json.dumps({
        "card_number": card_number,
        "name": worker.full_name,
        "valid_until": valid_until.isoformat(),
        "verify_url": verify_url,
    })
    qr_path = _generate_qr_image(qr_data)
    c.drawImage(qr_path, 8 * mm, 4 * mm, width=22 * mm, height=22 * mm)

    # Footer
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 7)
    c.drawString(34 * mm, 8 * mm, "Scan QR to verify authenticity")
    c.drawString(34 * mm, 4 * mm, f"Issued by: Labour Dept, Gujarat  |  Ref: {application.reference_id}")

    c.save()

    # Upload to S3
    s3_key = f"id_cards/{worker.id}/{card_number}.pdf"
    try:
        s3_url = _upload_pdf_to_s3(buffer, s3_key)
    except Exception as exc:
        logger.exception("Could not upload ID card PDF to S3: %s", exc)
        s3_url = ""

    return s3_key, s3_url, valid_until, qr_data