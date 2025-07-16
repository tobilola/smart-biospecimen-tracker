# 🧬 Smart Biospecimen Lifecycle Tracker

A lab-ready **Streamlit** app for tracking biospecimen samples across their lifecycle — from registration to usage, expiry, and archival. Built with Firebase backend, barcode integration, and real-time updates for volume and expiry monitoring.

🔗 [View Live App on Render](https://smart-biospecimen-tracker.onrender.com)

---

## 🚀 Key Features

✅ Register and update biospecimens with metadata (type, volume, location, expiry) 
✅ Store and retrieve records in real time via Firebase Firestore  
✅ Generate sample IDs automatically  
✅ Visual storage location input  
✅ Volume and expiry monitoring (Phase 2)  
✅ QR/Barcode generation for labeling (Phase 3)  
✅ Alert system for volume/expiry triggers (Phase 4)  

---

## 📸 Screenshot

![App Screenshot](app_screenshot.png)

---

## 🛠 Tech Stack

| Layer         | Tool/Tech             | Purpose                            |
|---------------|------------------------|-------------------------------------|
| Frontend      | Streamlit              | UI, forms, dashboard                |
| Backend DB    | Firebase Firestore     | Real-time document database         |
| Barcode/QR    | `python-barcode`, `qrcode` | (Planned) Sample labeling       |
| Scheduler     | `schedule`, `cron`, or Firebase Functions | Expiry & volume alerts |
| Auth (opt.)   | Firebase Auth          | Role-based access (future)          |

---

## 📁 Project Structure

