import streamlit as st
from firebase_config import db
from datetime import datetime
import uuid

st.set_page_config(page_title="Smart Biospecimen Tracker", layout="wide")

st.title("🧬 Smart Biospecimen Lifecycle Tracker")
st.subheader("📦 Register New Sample")

with st.form("register_sample"):
    sample_id = st.text_input("Sample ID", value=str(uuid.uuid4())[:8])
    sample_type = st.selectbox("Sample Type", ["Blood", Tissue", "Saliva", "Urine", "Plasma"])
    volume = st.number_input("Volume (µL)", min_value=0.0)
    location = st.text_input("Storage Location", placeholder="Freezer A / Shelf 1 / Box 3")
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

st.markdown("---")
st.subheader("📋 Registered Samples")

samples_ref = db.collection("samples")
samples = samples_ref.stream()

data = []
for doc in samples:
    item = doc.to_dict()
    data.append([
        item.get("sample_id"),
        item.get("type"),
        item.get("volume"),
        item.get("location"),
        item.get("expiry"),
        item.get("created_at")
    ])

if data:
    st.dataframe(
        data,
        column_config={
            0: "Sample ID",
            1: "Type",
            2: "Volume (µL)",
            3: "Storage Location",
            4: "Expiry Date",
            5: "Registered At"
        },
        use_container_width=True
    )
else:
    st.info("No samples registered yet.")


