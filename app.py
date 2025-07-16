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

    if submitted:
        db.collection("samples").document(sample_id).set({
            "sample_id": sample_id,
            "type": sample_type,
            "volume": volume,
            "location": location,
            "expiry": expiry_date.strftime("%Y-%m-%d"),
            "created_at": datetime.now().isoformat()
        })
        st.success(f"✅ Sample {sample_id} registered successfully!")

# -----------------------------
# View Registered Samples
# -----------------------------

import pandas as pd
from datetime import datetime, timedelta

st.markdown("---")
st.subheader("📋 Registered Samples with Alerts")

samples_ref = db.collection("samples")
samples = samples_ref.stream()

data = []
for doc in samples:
    item = doc.to_dict()

    # Parse expiry and volume
    expiry_raw = item.get("expiry")
    expiry_date = datetime.strptime(expiry_raw, "%Y-%m-%d")
    volume = item.get("volume")

    # Determine alerts
    alerts = []
    if expiry_date <= datetime.now() + timedelta(days=7):
        alerts.append("⚠️ Expiring Soon")
    if volume < 10:
        alerts.append("⚠️ Low Volume")

    alert_msg = " | ".join(alerts) if alerts else "✅ OK"

    # Build record
    data.append({
        "Sample ID": item.get("sample_id"),
        "Type": item.get("type"),
        "Volume (µL)": volume,
        "Storage Location": item.get("location"),
        "Expiry Date": expiry_raw,
        "Registered At": item.get("created_at"),
        "⚠️ Alert": alert_msg
    })

# Display
if data:
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
else:
    st.info("No samples registered yet.")




