"""MSG91 SMS integration helpers."""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _is_dev_mode() -> bool:
    """Return True if MSG91 is configured with placeholder credentials."""
    api_key = getattr(settings, "MSG91_API_KEY", "")
    return api_key.startswith("your_") or not api_key


def send_otp_sms(phone_number: str, otp_code: str):
    """Send OTP SMS using MSG91 or log to console in development."""
    if _is_dev_mode():
        logger.info("[DEV] OTP for %s: %s", phone_number, otp_code)
        print(f"[DEV] OTP for {phone_number}: {otp_code}")
        return {"dev": True}

    url = "https://api.msg91.com/api/v5/otp"
    payload = {
        "template_id": settings.MSG91_TEMPLATE_ID,
        "mobile": f"91{phone_number}",
        "authkey": settings.MSG91_API_KEY,
        "otp": otp_code,
    }
    response = requests.post(url, json=payload, timeout=10)
    logger.info("MSG91 OTP response status=%s body=%s", response.status_code, response.text)
    return response.json()


def send_sms(phone_number: str, message: str):
    """Send a generic SMS via MSG91 or log to console in development."""
    if _is_dev_mode():
        logger.info("[DEV] SMS to %s: %s", phone_number, message)
        print(f"[DEV] SMS to {phone_number}: {message}")
        return None

    url = "https://api.msg91.com/api/sendhttp.php"
    params = {
        "authkey": settings.MSG91_API_KEY,
        "mobiles": f"91{phone_number}",
        "message": message,
        "sender": settings.MSG91_SENDER_ID,
        "route": "4",
    }
    response = requests.get(url, params=params, timeout=10)
    logger.info("MSG91 SMS response status=%s body=%s", response.status_code, response.text)
    return response

