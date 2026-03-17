"""Web views for the worker portal."""

import logging
import time

import boto3
import requests
from django.contrib import messages
from django.shortcuts import redirect, render

from applications.models import Application
from documents.models import Document
from workers.models import Worker, WorkerProfile

logger = logging.getLogger(__name__)

API_BASE = "http://127.0.0.1:8000/api"

def home_view(request):
    """Homepage."""
    return render(request, "home.html")

def _get_worker(request):
    """Get worker from session."""
    worker_id = request.session.get("worker_id")
    if not worker_id:
        return None
    try:
        return Worker.objects.get(id=worker_id)
    except Worker.DoesNotExist:
        return None


def _login_required(view_func):
    """Simple session-based login check."""
    def wrapper(request, *args, **kwargs):
        if not request.session.get("worker_id"):
            return redirect("/worker/login/")
        return view_func(request, *args, **kwargs)
    return wrapper


def login_view(request):
    """Phone number entry screen."""
    if request.method == "POST":
        phone = request.POST.get("phone_number", "").strip()
        if not phone or len(phone) != 10 or not phone.isdigit():
            messages.error(request, "Please enter a valid 10-digit mobile number.")
            return render(request, "worker/login.html")
        try:
            resp = requests.post(
                f"{API_BASE}/auth/request-otp/",
                json={"phone_number": phone},
                timeout=10
            )
            data = resp.json()
            if data.get("success"):
                request.session["otp_phone"] = phone
                if data.get("debug_otp"):
                    messages.info(request, f"[DEV] OTP: {data['debug_otp']}")
                return redirect("/worker/otp/")
            else:
                messages.error(request, data.get("message", "Could not send OTP."))
        except Exception as e:
            logger.exception("OTP request failed: %s", e)
            messages.error(request, "Something went wrong. Please try again.")
    return render(request, "worker/login.html")


def otp_view(request):
    """OTP verification screen."""
    phone = request.session.get("otp_phone")
    if not phone:
        return redirect("/worker/login/")
    if request.method == "POST":
        otp_code = request.POST.get("otp_code", "").strip()
        phone = request.POST.get("phone_number", phone)
        try:
            resp = requests.post(
                f"{API_BASE}/auth/verify-otp/",
                json={"phone_number": phone, "otp_code": otp_code},
                timeout=10
            )
            data = resp.json()
            if data.get("success"):
                d = data["data"]
                request.session["worker_id"] = d["worker_id"]
                request.session["access_token"] = d["access"]
                request.session["refresh_token"] = d["refresh"]
                del request.session["otp_phone"]
                messages.success(request, "Login successful!")
                return redirect("/worker/dashboard/")
            else:
                messages.error(request, data.get("message", "Invalid OTP."))
        except Exception as e:
            logger.exception("OTP verify failed: %s", e)
            messages.error(request, "Something went wrong. Please try again.")
    return render(request, "worker/otp.html", {"phone_number": phone})


@_login_required
def dashboard_view(request):
    """Worker dashboard."""
    worker = _get_worker(request)
    if not worker:
        return redirect("/worker/login/")
    has_work_profile = WorkerProfile.objects.filter(worker=worker).exists()
    has_aadhaar = Document.objects.filter(worker=worker, doc_type="aadhaar").exists()
    has_photo = Document.objects.filter(worker=worker, doc_type="photo").exists()
    application = Application.objects.filter(worker=worker).first()
    return render(request, "worker/dashboard.html", {
        "worker": worker,
        "has_work_profile": has_work_profile,
        "has_aadhaar": has_aadhaar,
        "has_photo": has_photo,
        "application": application,
    })


@_login_required
def profile_view(request):
    """Personal details form."""
    worker = _get_worker(request)
    if request.method == "POST":
        worker.full_name = request.POST.get("full_name", "")
        worker.date_of_birth = request.POST.get("date_of_birth") or None
        worker.gender = request.POST.get("gender", "")
        worker.address = request.POST.get("address", "")
        worker.city = request.POST.get("city", "")
        worker.state = request.POST.get("state", "")
        worker.pincode = request.POST.get("pincode", "")
        worker.is_profile_complete = bool(
            worker.full_name and worker.date_of_birth
            and worker.gender and worker.address
        )
        worker.save()
        messages.success(request, "Personal details saved!")
        return redirect("/worker/dashboard/")
    return render(request, "worker/profile.html", {"worker": worker})


@_login_required
def work_details_view(request):
    """Work details form."""
    worker = _get_worker(request)
    profile, _ = WorkerProfile.objects.get_or_create(worker=worker)
    if request.method == "POST":
        profile.work_type = request.POST.get("work_type", "")
        profile.years_experience = int(request.POST.get("years_experience", 0))
        profile.languages_known = request.POST.get("languages_known", "")
        profile.availability = request.POST.get("availability", "")
        salary = request.POST.get("expected_salary")
        profile.expected_salary = int(salary) if salary else None
        profile.save()
        messages.success(request, "Work details saved!")
        return redirect("/worker/dashboard/")
    return render(request, "worker/work_details.html", {"profile": profile})


@_login_required
def documents_view(request):
    """Document upload screen with AI results."""
    worker = _get_worker(request)
    has_aadhaar = Document.objects.filter(worker=worker, doc_type="aadhaar").exists()
    has_photo = Document.objects.filter(worker=worker, doc_type="photo").exists()
    quality_issues = request.session.pop("quality_issues", None)
    ocr_data = request.session.pop("ocr_data", None)
    match_result = request.session.pop("match_result", None)
    return render(request, "worker/documents.html", {
        "has_aadhaar": has_aadhaar,
        "has_photo": has_photo,
        "quality_issues": quality_issues,
        "ocr_data": ocr_data,
        "match_result": match_result,
    })


@_login_required
def upload_aadhaar_view(request):
    """Handle Aadhaar upload with AI quality check, OCR, and verification."""
    if request.method == "POST":
        worker = _get_worker(request)
        file_obj = request.FILES.get("file")
        upload_mode = request.POST.get("upload_mode", "manual")

        if not file_obj:
            messages.error(request, "Please select a file.")
            return redirect("/worker/documents/")

        filename = file_obj.name.lower()
        if not any(filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
            messages.error(request, "Please upload Aadhaar as a JPG or PNG image, not PDF. Take a photo of your Aadhaar card.")
            return redirect("/worker/documents/")

        if file_obj.size > 5 * 1024 * 1024:
            messages.error(request, "File size must be under 5MB.")
            return redirect("/worker/documents/")

        # ── STEP 1: Quality check (images only, not PDF) ──────────────────
        if not filename.endswith(".pdf"):
            from .ai_services import check_document_quality
            quality_result = check_document_quality(file_obj)
            logger.info("Quality result: %s", quality_result)
            print(f"QUALITY CHECK: {quality_result}")
            if not quality_result["is_good"]:
                request.session["quality_issues"] = quality_result["issues"]
                messages.error(
                    request,
                    f"Document quality check failed (score: {quality_result['score']}/100). "
                    "Please upload a clearer image."
                )
                return redirect("/worker/documents/")

        # ── STEP 2: OCR extraction ─────────────────────────────────────────
        ocr_data = None
        if not filename.endswith(".pdf"):
            from .ai_services import extract_aadhaar_data
            ocr_data = extract_aadhaar_data(file_obj)
            request.session["ocr_data"] = ocr_data
            logger.info("OCR result: %s", ocr_data)
            print(f"OCR RESULT: {ocr_data}")


        # ── STEP 3a: Manual mode — verify entered data vs Aadhaar ─────────
        if upload_mode == "manual" and ocr_data:
            if worker.full_name or worker.date_of_birth or worker.gender:
                from .ai_services import verify_aadhaar_match
                manual_data = {
                    "full_name": worker.full_name or "",
                    "date_of_birth": str(worker.date_of_birth) if worker.date_of_birth else "",
                    "gender": worker.gender or "",
                    "pincode": worker.pincode or "",
                }
                match_result = verify_aadhaar_match(ocr_data, manual_data)
                request.session["match_result"] = match_result
                logger.info("Match result: %s", match_result)
                if not match_result["is_match"]:
                    messages.warning(
                        request,
                        f"Aadhaar details don't fully match your profile "
                        f"({match_result['overall_score']}% match). Please review carefully."
                    )
                else:
                    messages.success(
                        request,
                        f"Aadhaar verified! {match_result['overall_score']}% match with your profile."
                    )
            else:
                messages.info(
                    request,
                    "Please fill your Personal Details first, then re-upload "
                    "in Manual mode to verify against Aadhaar."
                )

        # ── STEP 3b: Auto-fill mode — save OCR data to worker profile ─────
        if upload_mode == "auto" and ocr_data:
            filled_fields = []
            if ocr_data.get("name"):
                worker.full_name = ocr_data["name"]
                filled_fields.append(f"Name: {ocr_data['name']}")
            if ocr_data.get("date_of_birth"):
                from datetime import datetime
                try:
                    worker.date_of_birth = datetime.strptime(
                        ocr_data["date_of_birth"], "%Y-%m-%d"
                    ).date()
                    filled_fields.append(f"DOB: {ocr_data['date_of_birth']}")
                except Exception:
                    pass
            if ocr_data.get("gender"):
                worker.gender = ocr_data["gender"]
                filled_fields.append(f"Gender: {ocr_data['gender']}")
            if ocr_data.get("pincode"):
                worker.pincode = ocr_data["pincode"]
                filled_fields.append(f"Pincode: {ocr_data['pincode']}")
            if ocr_data.get("address") and not worker.address:
                worker.address = ocr_data["address"]
                filled_fields.append("Address")
            worker.is_profile_complete = bool(
                worker.full_name and worker.date_of_birth and worker.gender
            )
            worker.save()

            if filled_fields:
                messages.success(
                    request,
                    f"Profile auto-filled from Aadhaar! "
                    f"Filled: {', '.join(filled_fields)}. "
                    f"Please review your profile."
                )
            else:
                messages.warning(
                    request,
                    "Aadhaar uploaded but could not auto-extract details. "
                    "Please fill your profile manually."
                )

        # ── STEP 4: Save document record ──────────────────────────────────
        try:
            from django.conf import settings
            key = f"documents/{worker.id}/aadhaar/{int(time.time())}_{file_obj.name}"
            bucket = settings.AWS_STORAGE_BUCKET_NAME

            if bucket and not settings.AWS_ACCESS_KEY_ID.startswith("your_"):
                client = boto3.client(
                    "s3",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME,
                )
                file_obj.seek(0)
                client.upload_fileobj(file_obj, bucket, key)
                s3_url = (
                    f"https://{bucket}.s3."
                    f"{settings.AWS_S3_REGION_NAME}.amazonaws.com/{key}"
                )
            else:
                s3_url = f"/media/{key}"

            Document.objects.update_or_create(
                worker=worker, doc_type="aadhaar",
                defaults={
                    "s3_key": key,
                    "s3_url": s3_url,
                    "file_size": file_obj.size,
                }
            )

            if upload_mode == "auto":
                return redirect("/worker/profile/")
            else:
                return redirect("/worker/documents/")

        except Exception as e:
            logger.exception("Aadhaar upload error: %s", e)
            messages.error(request, "Upload failed. Please try again.")

    return redirect("/worker/documents/")


@_login_required
def upload_photo_view(request):
    """Handle photo file upload."""
    if request.method == "POST":
        worker = _get_worker(request)
        file_obj = request.FILES.get("file")
        if not file_obj:
            messages.error(request, "Please select a file.")
            return redirect("/worker/documents/")
        filename = file_obj.name.lower()
        if not any(filename.endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
            messages.error(request, "Only JPG, PNG files allowed.")
            return redirect("/worker/documents/")
        if file_obj.size > 2 * 1024 * 1024:
            messages.error(request, "File size must be under 2MB.")
            return redirect("/worker/documents/")
        try:
            from django.conf import settings
            key = f"documents/{worker.id}/photo/{int(time.time())}_{file_obj.name}"
            bucket = settings.AWS_STORAGE_BUCKET_NAME
            if bucket and not settings.AWS_ACCESS_KEY_ID.startswith("your_"):
                client = boto3.client(
                    "s3",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    region_name=settings.AWS_S3_REGION_NAME,
                )
                client.upload_fileobj(file_obj, bucket, key)
                s3_url = (
                    f"https://{bucket}.s3."
                    f"{settings.AWS_S3_REGION_NAME}.amazonaws.com/{key}"
                )
            else:
                s3_url = f"/media/{key}"
            Document.objects.update_or_create(
                worker=worker, doc_type="photo",
                defaults={
                    "s3_key": key,
                    "s3_url": s3_url,
                    "file_size": file_obj.size,
                }
            )
            messages.success(request, "Photo uploaded successfully!")
        except Exception as e:
            logger.exception("Photo upload error: %s", e)
            messages.error(request, "Upload failed. Please try again.")
    return redirect("/worker/documents/")


@_login_required
def submit_application_view(request):
    """Submit the application."""
    if request.method == "POST":
        worker = _get_worker(request)
        app, created = Application.objects.get_or_create(worker=worker)
        if app.status not in ("approved",):
            app.set_submitted()
            app.save()
            try:
                from notifications.tasks import send_submission_sms
                send_submission_sms.delay(worker.phone_number, app.reference_id)
            except Exception:
                pass
            messages.success(
                request,
                f"Application submitted successfully! "
                f"Your Reference ID is: {app.reference_id}"
            )
        else:
            messages.info(request, "Your application is already approved!")
        return redirect("/worker/dashboard/")
    return redirect("/worker/dashboard/")


def logout_view(request):
    """Clear session and logout."""
    request.session.flush()
    messages.success(request, "Logged out successfully.")
    return redirect("/worker/login/")

@_login_required
def id_card_view(request):
    """Show ID card download page — generate synchronously if not exists."""
    worker = _get_worker(request)
    try:
        app = Application.objects.get(worker=worker)
        if app.status != "approved":
            messages.warning(request, "Your application is not approved yet.")
            return redirect("/worker/dashboard/")

        # Try to get existing ID card
        try:
            id_card = app.workeridcard
        except Exception:
            # Generate synchronously right now — no Celery needed
            from id_cards.models import WorkerIDCard
            from id_cards.generator import generate_worker_id_card

            try:
                card_number = WorkerIDCard.generate_card_number()
                s3_key, s3_url, valid_until, qr_data = generate_worker_id_card(
                    worker, app, card_number
                )
                id_card = WorkerIDCard.objects.create(
                    application=app,
                    card_number=card_number,
                    qr_code_data=qr_data,
                    pdf_s3_key=s3_key,
                    pdf_s3_url=s3_url,
                    valid_until=valid_until,
                )
                messages.success(request, "ID card generated successfully!")
            except Exception as e:
                logger.exception("ID card generation error: %s", e)
                # Generate a simple fallback without PDF
                from id_cards.models import WorkerIDCard
                from django.utils import timezone
                card_number = WorkerIDCard.generate_card_number()
                valid_until = WorkerIDCard.calculate_valid_until()
                id_card = WorkerIDCard.objects.create(
                    application=app,
                    card_number=card_number,
                    qr_code_data=f'{{"card": "{card_number}"}}',
                    pdf_s3_key="",
                    pdf_s3_url="",
                    valid_until=valid_until,
                )
                messages.info(
                    request,
                    "ID card created. PDF download requires AWS S3 configuration."
                )

        # Get worker photo URL
        worker_photo = None
        try:
            from documents.models import Document
            photo_doc = Document.objects.filter(
                worker=worker, doc_type="photo"
            ).first()
            if photo_doc:
                # Handle both S3 and local paths
                url = photo_doc.s3_url
                if url.startswith("/media"):
                    worker_photo = url
                elif url.startswith("http"):
                    worker_photo = url
                else:
                    worker_photo = f"/media/{url}"
                logger.info("Worker photo URL: %s", worker_photo)
        except Exception as e:
            logger.exception("Could not get worker photo: %s", e)

        return render(request, "worker/id_card.html", {
            "worker": worker,
            "id_card": id_card,
            "application": app,
            "worker_photo": worker_photo,
        })

    except Application.DoesNotExist:
        messages.error(request, "No application found.")
        return redirect("/worker/dashboard/")