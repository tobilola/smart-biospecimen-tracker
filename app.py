import streamlit as st
from firebase_config import db
from datetime import datetime, timedelta
import uuid
import qrcode
import io
import base64
import pandas as pd

from google.cloud.firestore import SERVER_TIMESTAMP

def log_sample_activity(sample_id, action, details):
    db.collection("samples").document(sample_id).collection("activity_log").add({
        "action": action,
        "details": details,
        "timestamp": SERVER_TIMESTAMP
    })

# PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image

# --------------------------------
# PDF label generator function
# --------------------------------

def generate_pdf(sample_id, sample_type, volume, location, expiry_date, qr_img):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, 750, f"Sample ID: {sample_id}")
    c.drawString(100, 730, f"Type: {sample_type}")
    c.drawString(100, 710, f"Volume: {volume} µL")
    c.drawString(100, 690, f"Location: {location}")
    c.drawString(100, 670, f"Expiry: {expiry_date}")

    # ✅ Convert QR to PIL Image if needed
    if not isinstance(qr_img, Image.Image):
        qr_img = qr_img.convert("RGB")  # Ensure it's a PIL image

    # ✅ Draw QR code directly
    c.drawInlineImage(qr_img, 100, 500, width=150, height=150)

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


# --------------------------------
# UI: Register Sample
# --------------------------------
st.set_page_config(page_title="Smart Biospecimen Tracker", layout="wide")
st.title("🧬 Smart Biospecimen Lifecycle Tracker")
st.subheader("📦 Register New Sample")

with st.form("register_sample"):
    sample_id = st.text_input("Sample ID", value=str(uuid.uuid4())[:8])
    sample_type = st.selectbox("Sample Type", ["Blood", "Tissue", "Saliva", "Urine", "Plasma"])
    volume = st.number_input("Volume (µL)", min_value=0.0)
    freezer = st.selectbox("Freezer", ["Freezer A", "Freezer B", "Freezer C"])
    rack = st.selectbox("Rack", [f"Rack {i}" for i in range(1, 6)])
    shelf = st.selectbox("Shelf", [f"Shelf {i}" for i in range(1, 5)])
    box = st.text_input("Box", placeholder="e.g., Box 6")
    location = f"{freezer} / {rack} / {shelf} / {box}"
    expiry_date = st.date_input("Expiry Date")
    submitted = st.form_submit_button("Register")

if submitted:
    # Save to Firebase
    db.collection("samples").document(sample_id).set({
        "sample_id": sample_id,
        "type": sample_type,
        "volume": volume,
        "location": location,
        "expiry": expiry_date.strftime("%Y-%m-%d"),
        "created_at": datetime.now().isoformat()
    })
    st.success(f"✅ Sample {sample_id} registered successfully!")

    log_sample_activity(
    sample_id,
    action="register_sample",
    details=f"Sample registered with volume {volume} µL at {location}."
)

   # Generate QR Code
    qr_data = f"ID: {sample_id}\nType: {sample_type}\nLocation: {location}\nExpiry: {expiry_date.strftime('%Y-%m-%d')}"
    qr_img = qrcode.make(qr_data).convert("RGB")  # Ensure QR is a PIL Image

  # Convert QR to bytes for PNG download
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_bytes = buffer.getvalue()

  # Display QR
    st.subheader("🧬 Sample QR Code")
    st.image(qr_bytes, caption="Scan to retrieve sample info", use_container_width=True)

  # PNG Download
    b64 = base64.b64encode(qr_bytes).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="sample_{sample_id}.png">📥 Download QR Code as PNG</a>'
    st.markdown(href, unsafe_allow_html=True)

# ✅ PDF Label
    pdf_buffer = generate_pdf(sample_id, sample_type, volume, location, expiry_date.strftime('%Y-%m-%d'), qr_img)
    b64_pdf = base64.b64encode(pdf_buffer.read()).decode()
    pdf_href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="label_{sample_id}.pdf">📄 Download Sample Label as PDF</a>'
    st.markdown(pdf_href, unsafe_allow_html=True)

# --------------------------------
# View Registered Samples
# --------------------------------
st.markdown("---")
st.subheader("📋 Registered Samples with Filters and Alerts")

samples_ref = db.collection("samples")
samples = samples_ref.stream()

data = []
for doc in samples:
    item = doc.to_dict()
    expiry_raw = item.get("expiry")
    expiry = datetime.strptime(expiry_raw, "%Y-%m-%d")
    volume = item.get("volume")
    alerts = []
    if expiry <= datetime.now() + timedelta(days=7):
        alerts.append("⚠️ Expiring Soon")
    if volume < 10:
        alerts.append("⚠️ Low Volume")
    alert = " | ".join(alerts) if alerts else "✅ OK"
    data.append({
        "Sample ID": item.get("sample_id"),
        "Type": item.get("type"),
        "Volume (µL)": volume,
        "Storage Location": item.get("location"),
        "Expiry Date": expiry_raw,
        "Registered At": item.get("created_at"),
        "⚠️ Alert": alert
    })

df = pd.DataFrame(data)

# Sidebar filters
st.sidebar.header("🔍 Filter Samples")
types = df["Type"].unique().tolist()
alerts = df["⚠️ Alert"].unique().tolist()
selected_types = st.sidebar.multiselect("Sample Type", types, default=types)
selected_alerts = st.sidebar.multiselect("Alert Status", alerts, default=alerts)
min_v, max_v = float(df["Volume (µL)"].min()), float(df["Volume (µL)"].max())
volume_range = st.sidebar.slider("Volume Range (µL)", 0.0, max_v, (min_v, max_v))

# Filter data
filtered_df = df[
    (df["Type"].isin(selected_types)) &
    (df["⚠️ Alert"].isin(selected_alerts)) &
    (df["Volume (µL)"] >= volume_range[0]) &
    (df["Volume (µL)"] <= volume_range[1])
]

if not filtered_df.empty:
    st.dataframe(filtered_df, use_container_width=True)
    csv = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button("⬇️ Download CSV of Samples", csv, "biospecimen_samples.csv", "text/csv")
else:
    st.info("No samples match the current filter.")
