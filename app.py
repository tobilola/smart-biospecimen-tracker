import streamlit as st
from firebase_config import db
from datetime import datetime
import uuid

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

import qrcode
from PIL import Image
import io

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

    # Generate QR Code
    qr_data = f"ID: {sample_id}\nType: {sample_type}\nLocation: {location}\nExpiry: {expiry_date.strftime('%Y-%m-%d')}"
    qr_img = qrcode.make(qr_data)

    # Convert to bytes
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    byte_qr = buf.getvalue()

    # Display QR
    st.subheader("🧬 Sample QR Code")
    st.image(byte_qr, caption="Scan to retrieve sample info", use_container_width=True)

# -----------------------------
# View Registered Samples
# -----------------------------

import pandas as pd
from datetime import datetime, timedelta

st.markdown("---")
st.subheader("📋 Registered Samples with Filters and Alerts")

# Fetch data from Firestore
samples_ref = db.collection("samples")
samples = samples_ref.stream()

data = []
for doc in samples:
    item = doc.to_dict()

    expiry_raw = item.get("expiry")
    expiry_date = datetime.strptime(expiry_raw, "%Y-%m-%d")
    volume = item.get("volume")

    alerts = []
    if expiry_date <= datetime.now() + timedelta(days=7):
        alerts.append("⚠️ Expiring Soon")
    if volume < 10:
        alerts.append("⚠️ Low Volume")
    alert_msg = " | ".join(alerts) if alerts else "✅ OK"

    data.append({
        "Sample ID": item.get("sample_id"),
        "Type": item.get("type"),
        "Volume (µL)": volume,
        "Storage Location": item.get("location"),
        "Expiry Date": expiry_raw,
        "Registered At": item.get("created_at"),
        "⚠️ Alert": alert_msg
    })

# Convert to DataFrame
df = pd.DataFrame(data)

# ✅ Sidebar filters
st.sidebar.header("🔍 Filter Samples")

# Sample type filter
sample_types = df["Type"].unique().tolist()
selected_types = st.sidebar.multiselect("Sample Type", sample_types, default=sample_types)

# Alert filter
alert_options = df["⚠️ Alert"].unique().tolist()
selected_alerts = st.sidebar.multiselect("Alert Status", alert_options, default=alert_options)

# Volume filter
min_volume, max_volume = float(df["Volume (µL)"].min()), float(df["Volume (µL)"].max())
volume_range = st.sidebar.slider("Volume Range (µL)", min_value=0.0, max_value=max_volume, value=(min_volume, max_volume))

# ✅ Apply filters
filtered_df = df[
    (df["Type"].isin(selected_types)) &
    (df["⚠️ Alert"].isin(selected_alerts)) &
    (df["Volume (µL)"] >= volume_range[0]) &
    (df["Volume (µL)"] <= volume_range[1])
]

# ✅ Show table
if not filtered_df.empty:
    st.dataframe(filtered_df, use_container_width=True)
else:
    st.warning("No samples match the selected filters.")
