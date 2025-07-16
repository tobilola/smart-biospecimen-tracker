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


