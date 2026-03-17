# 🏛️ Domestic Worker Registration Portal

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2.9-092E20?style=flat&logo=django&logoColor=white)](https://www.djangoproject.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A full-stack, government-grade registration system designed to provide formal identity and documentation to India's undocumented domestic workforce.

---

## 📌 Project Overview

Domestic workers (maids, cooks, drivers, gardeners) in India often lack formal proof of employment and government identity, excluding them from welfare benefits and social security. 

**The Solution:** This portal allows workers to register via a mobile-friendly web interface using OTP authentication, AI-powered document verification, and OCR. Upon government approval, workers receive a verified **Digital ID Card** with a unique QR code.

> **Placement Note:** This project was developed for the technical round at **Pravi (Ahmedabad)** to solve large-scale grievance and registration workflows.

---

## 🚀 Key Features

### 👤 Worker Portal
* **Secure Auth:** Phone-based login with OTP verification.
* **AI Document Guard:** 3-layer Aadhaar verification:
    * *Quality Check:* Detects blur, brightness, and resolution issues using **Pillow**.
    * *Auto-Fill (OCR):* Extracts Name, DOB, and Address using **Tesseract OCR**.
    * *Cross-Verification:* Matches manual input against OCR data for accuracy.
* **Status Tracking:** Real-time tracking of application lifecycle (Draft → Under Review → Approved).
* **Digital ID:** Dynamic PDF generation with photo and secure QR code.

### 🛡️ Officer (Admin) Portal
* **Central Dashboard:** Comprehensive view of all state-wide applications.
* **Workflow Automation:** One-click Approve/Reject with automated SMS triggers.
* **Advanced Filtering:** Filter by pincode, work type, or registration date.

---

## 🛠️ Tech Stack

### Backend & AI
| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **Framework** | Django 4.2.9 + DRF | Core Logic & REST APIs |
| **Auth** | SimpleJWT | Secure Token-based Authentication |
| **AI/OCR** | Tesseract + OpenCV | Image Pre-processing & Data Extraction |
| **Image Processing**| Pillow (PIL) | Document Quality & Blur Detection |
| **Tasks** | Celery + Redis | Async SMS & PDF Generation |

### Frontend & Infrastructure
| Component | Technology | Purpose |
| :--- | :--- | :--- |
| **UI** | Bootstrap 5 + JS | Mobile-first Responsive Design |
| **Database** | PostgreSQL 16 | Production-grade Relational Data |
| **Storage** | AWS S3 | Secure storage for IDs and Aadhaar images |
| **Deployment** | Docker & Compose | Containerized Environment |

---

## 📂 Project Structure

```text
domestic-worker-reg/
├── accounts/           # Auth, OTP, and JWT logic
├── workers/            # Profile and experience management
├── documents/          # AI-powered document processing
├── applications/       # Registration workflow & status tracking
├── id_cards/           # ReportLab PDF & QR generation logic
├── config/             # Root settings & Celery config
└── templates/          # Responsive HTML interfaces
