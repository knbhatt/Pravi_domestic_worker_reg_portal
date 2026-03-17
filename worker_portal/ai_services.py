"""AI services for Aadhaar verification, OCR, and quality check."""

import logging
import re
import io

import numpy as np
import pytesseract
from PIL import Image, ImageFilter

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

logger = logging.getLogger(__name__)


def check_document_quality(image_file) -> dict:
    """
    Check if uploaded document image is good quality.
    Uses PIL only — no OpenCV dependency issues.
    """
    try:
        image_file.seek(0)
        img = Image.open(image_file).convert('L')
        image_file.seek(0)

        issues = []
        score = 100

        # Check image size
        w, h = img.size
        if w < 300 or h < 200:
            issues.append("Image resolution is too low. Use a higher quality photo.")
            score -= 30

        # Check brightness
        arr = np.array(img).astype(np.float32)
        brightness = float(np.mean(arr))
        if brightness < 50:
            issues.append("Image is too dark. Please take photo in better lighting.")
            score -= 30
        elif brightness > 230:
            issues.append("Image is overexposed. Avoid direct flash or sunlight.")
            score -= 20

        # Blur detection using edge variance
        # Real documents (Aadhaar) have sharp text edges — variance > 1000
        # Blurry images have variance < 500
        edge_img = img.filter(ImageFilter.FIND_EDGES)
        edge_arr = np.array(edge_img).astype(np.float32)
        edge_variance = float(np.var(edge_arr))
        logger.info("Edge variance (blur score): %s", edge_variance)

        if edge_variance < 300:
            issues.append("Image is too blurry. Please retake with a steady hand in good light.")
            score -= 50
        elif edge_variance < 600:
            issues.append("Image is slightly blurry. A clearer photo is recommended.")
            score -= 20

        # Aspect ratio check for Aadhaar (should be landscape ~1.58 ratio)
        if w > 0 and h > 0:
            ratio = w / h
            if ratio < 1.1 or ratio > 2.5:
                issues.append("Image may be cropped incorrectly. Aadhaar should be landscape.")
                score -= 15

        score = max(0, score)
        logger.info("Quality score: %s, issues: %s, edge_variance: %s",
                    score, issues, edge_variance)

        return {
            "is_good": score >= 55,
            "issues": issues,
            "score": score,
            "brightness": round(brightness, 1),
            "edge_variance": round(edge_variance, 1),
        }

    except Exception as exc:
        logger.exception("Error checking document quality: %s", exc)
        return {"is_good": True, "issues": [], "score": 100}


def extract_aadhaar_data(image_file) -> dict:
    """
    Extract text from Aadhaar card image using OCR.
    """
    try:
        image_file.seek(0)
        img = Image.open(image_file).convert('RGB')
        image_file.seek(0)

        # Enhance image for better OCR
        import numpy as np
        import cv2
        img_array = np.array(img)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        processed = Image.fromarray(thresh)

        # Run OCR
        text = pytesseract.image_to_string(
            processed,
            config='--psm 3 --oem 3'
        )
        logger.info("OCR raw text:\n%s", text)

        extracted = {
            "raw_text": text,
            "name": None,
            "date_of_birth": None,
            "gender": None,
            "address": None,
            "pincode": None,
            "aadhaar_number": None,
        }

        lines = [l.strip() for l in text.split('\n') if l.strip()]

        # Aadhaar number
        for line in lines:
            match = re.search(r'\b\d{4}\s?\d{4}\s?\d{4}\b', line)
            if match:
                extracted["aadhaar_number"] = match.group().replace(" ", "")
                break

        # DOB
        for line in lines:
            match = re.search(
                r'(?:DOB|Date of Birth|Birth)[:\s]+(\d{2}[/-]\d{2}[/-]\d{4})',
                line, re.IGNORECASE
            )
            if not match:
                match = re.search(r'\b(\d{2}[/-]\d{2}[/-]\d{4})\b', line)
            if match:
                try:
                    from datetime import datetime
                    dob_str = match.group(1).replace('-', '/')
                    dob = datetime.strptime(dob_str, '%d/%m/%Y')
                    extracted["date_of_birth"] = dob.strftime('%Y-%m-%d')
                    break
                except Exception:
                    pass

        # Gender
        for line in lines:
            upper = line.upper()
            if 'FEMALE' in upper:
                extracted["gender"] = "F"
                break
            elif 'MALE' in upper:
                extracted["gender"] = "M"
                break

        # Pincode
        for line in lines:
            match = re.search(r'\b([1-9]\d{5})\b', line)
            if match:
                extracted["pincode"] = match.group(1)
                break

        # Name — skip known non-name lines
        skip = [
            'government', 'india', 'aadhaar', 'unique', 'authority',
            'dob', 'date', 'birth', 'male', 'female', 'uid', 'help',
            'www', 'uidai', 'enrollment', 'vid', 'download', 'year',
        ]
        for line in lines:
            if len(line) < 3:
                continue
            if any(s in line.lower() for s in skip):
                continue
            if re.search(r'\d{3,}', line):
                continue
            if re.match(r'^[A-Za-z][A-Za-z\s\.]{2,49}$', line):
                extracted["name"] = line.strip()
                break

        # Address
        addr_keywords = [
            'house', 'flat', 'road', 'street', 'nagar', 'colony',
            'near', 'village', 'dist', 'ward', 'sector', 'taluka',
            'po ', 's/o', 'w/o', 'd/o', 'c/o'
        ]
        addr_lines = []
        for line in lines:
            if any(k in line.lower() for k in addr_keywords):
                addr_lines.append(line)
            elif extracted["pincode"] and extracted["pincode"] in line:
                addr_lines.append(line)
        if addr_lines:
            extracted["address"] = ', '.join(addr_lines[:3])

        logger.info("Extracted data: %s", {k: v for k, v in extracted.items() if k != 'raw_text'})
        return extracted

    except Exception as exc:
        logger.exception("Error in OCR extraction: %s", exc)
        return {
            "raw_text": "", "name": None, "date_of_birth": None,
            "gender": None, "address": None, "pincode": None, "aadhaar_number": None,
        }


def verify_aadhaar_match(extracted_data: dict, manual_data: dict) -> dict:
    """Compare manually entered data against OCR extracted data."""
    results = {}
    total_score = 0
    checked_fields = 0

    # Name match
    ocr_name = (extracted_data.get("name") or "").lower().strip()
    manual_name = (manual_data.get("full_name") or "").lower().strip()
    if ocr_name and manual_name:
        checked_fields += 1
        ocr_words = set(ocr_name.split())
        manual_words = set(manual_name.split())
        common = ocr_words & manual_words
        if common:
            name_score = min(100, int(len(common) / max(len(ocr_words), len(manual_words)) * 100) + 40)
        else:
            name_score = 0
        results["name"] = {
            "match": name_score >= 50,
            "score": name_score,
            "ocr_value": extracted_data.get("name"),
            "entered_value": manual_data.get("full_name"),
        }
        total_score += name_score

    # DOB match
    ocr_dob = (extracted_data.get("date_of_birth") or "").strip()
    manual_dob = (manual_data.get("date_of_birth") or "").strip()
    if ocr_dob and manual_dob:
        checked_fields += 1
        match = ocr_dob == manual_dob
        results["date_of_birth"] = {
            "match": match, "score": 100 if match else 0,
            "ocr_value": ocr_dob, "entered_value": manual_dob,
        }
        total_score += 100 if match else 0

    # Gender match
    ocr_gender = (extracted_data.get("gender") or "").upper().strip()
    manual_gender = (manual_data.get("gender") or "").upper().strip()
    if ocr_gender and manual_gender:
        checked_fields += 1
        match = ocr_gender == manual_gender
        results["gender"] = {
            "match": match, "score": 100 if match else 0,
            "ocr_value": ocr_gender, "entered_value": manual_gender,
        }
        total_score += 100 if match else 0

    # Pincode match
    ocr_pin = (extracted_data.get("pincode") or "").strip()
    manual_pin = (manual_data.get("pincode") or "").strip()
    if ocr_pin and manual_pin:
        checked_fields += 1
        match = ocr_pin == manual_pin
        results["pincode"] = {
            "match": match, "score": 100 if match else 0,
            "ocr_value": ocr_pin, "entered_value": manual_pin,
        }
        total_score += 100 if match else 0

    overall = int(total_score / checked_fields) if checked_fields > 0 else 0

    return {
        "overall_score": overall,
        "is_match": overall >= 50,
        "checked_fields": checked_fields,
        "field_results": results,
        "message": "Details match Aadhaar card." if overall >= 50
                   else "Some details don't match your Aadhaar. Please check and correct.",
    }