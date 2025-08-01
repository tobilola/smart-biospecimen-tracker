import streamlit as st
from auth_utils import login_user, logout_user
from firebase_config import db
from datetime import datetime, timedelta
import uuid
import qrcode
import io
import base64
import pandas as pd
from google.cloud.firestore import SERVER_TIMESTAMP
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image
import plotly.express as px

# ✅ Page config and responsive sidebar
st.set_page_config(page_title="Smart Biospecimen Tracker", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
        @media (max-width: 768px) {
            [data-testid="stSidebar"] {
                display: none;
            }
        }
    </style>
""", unsafe_allow_html=True)

# ✅ PDF label generator
def generate_pdf(sample_id, sample_type, volume, location, expiry_date, qr_img):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, 750, f"Sample ID: {sample_id}")
    c.drawString(100, 730, f"Type: {sample_type}")
    c.drawString(100, 710, f"Volume: {volume} µL")
    c.drawString(100, 690, f"Location: {location}")
    c.drawString(100, 670, f"Expiry: {expiry_date}")
    c.drawInlineImage(qr_img, 100, 500, width=150, height=150)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# ✅ Sample activity logger
def log_sample_activity(sample_id, action, details):
    log_entry = {
        "action": action,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    db.collection("samples").document(sample_id).collection("activity_log").add(log_entry)

# ✅ Show login form
def show_login_page():
    st.title("🔐 Login to Smart Biospecimen Tracker")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login", key="login_button"):
        login_user(email, password)

# ✅ Show main app (visible only when logged in)
def show_main_app():
    user = st.session_state["user"]
    st.sidebar.markdown(f"👤 Logged in as: `{user['email']}`")
    role = user.get("role", "Technician")
    st.sidebar.markdown(f"🛡 Role: `{role}`")
    if st.sidebar.button("🚪 Logout", key=f"logout_button_{user['email']}"):
        logout_user()
        st.experimental_rerun()

    st.title("🧬 Smart Biospecimen Lifecycle Tracker")
    st.subheader("📦 Register New Sample")

    # Registration form
    with st.form("register_sample"):
        sample_id = st.text_input("Sample ID", value=str(uuid.uuid4())[:8], disabled=True)
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
        try:
            log_sample_activity(
                sample_id,
                action="register_sample",
                details=f"Sample registered with volume {volume} µL at {location}."
            )
            st.info("📌 Activity logged.")
        except Exception as e:
            st.error(f"❌ Logging failed: {e}")

    # 📜 Activity Log
    st.markdown("---")
    st.subheader("📜 View Sample Activity Log")
    sample_id_input = st.text_input("🔍 Enter Sample ID")
    if st.button("View Activity Log"):
        try:
            log_ref = db.collection("samples").document(sample_id_input).collection("activity_log").order_by("timestamp").stream()
            logs = [{
                "Timestamp": doc.to_dict().get("timestamp"),
                "Action": doc.to_dict().get("action"),
                "Details": doc.to_dict().get("details")
            } for doc in log_ref]
            if logs:
                log_df = pd.DataFrame(logs)
                st.dataframe(log_df)
            else:
                st.warning("No activity found for this sample.")
        except Exception as e:
            st.error(f"Error fetching log: {e}")

    # 📋 Registered Samples with Filters
    st.markdown("---")
    st.subheader("📋 Registered Samples with Filters and Alerts")
    samples = db.collection("samples").stream()
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
    st.sidebar.header("🔍 Filter Samples")
    types = df["Type"].unique().tolist()
    alerts = df["⚠️ Alert"].unique().tolist()
    selected_types = st.sidebar.multiselect("Sample Type", types, default=types)
    selected_alerts = st.sidebar.multiselect("Alert Status", alerts, default=alerts)
    min_v, max_v = float(df["Volume (µL)"].min()), float(df["Volume (µL)"].max())
    volume_range = st.sidebar.slider("Volume Range (µL)", 0.0, max_v, (min_v, max_v))

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

    # 📈 Filtered Analytics
    st.markdown("### 📊 Filtered Sample Analytics")
    col1, col2, col3 = st.columns(3)
    col1.metric("📦 Total Samples", len(filtered_df))
    col2.metric("⏰ Expiring Soon", filtered_df[filtered_df["⚠️ Alert"].str.contains("Expiring Soon")].shape[0])
    col3.metric("🧪 Low Volume", filtered_df[filtered_df["⚠️ Alert"].str.contains("Low Volume")].shape[0])
    st.plotly_chart(px.bar(filtered_df, x="Type", title="🧬 Sample Count by Type"), use_container_width=True)
    filtered_df["Freezer"] = filtered_df["Storage Location"].apply(lambda x: x.split(" / ")[0])
    st.plotly_chart(px.pie(filtered_df, names="Freezer", title="🗃️ Freezer Distribution"), use_container_width=True)

    # 🌐 Global Analytics
    st.markdown("### 🌐 Global Sample Analytics (All Data)")
    df["Expiry Date"] = pd.to_datetime(df["Expiry Date"])
    col1, col2, col3 = st.columns(3)
    col1.metric("🧮 Total Samples", len(df))
    col2.metric("⚠️ Expiring Soon (7 days)", df[df["Expiry Date"] <= datetime.today() + timedelta(days=7)].shape[0])
    col3.metric("🧪 Low Volume (<10 µL)", df[df["Volume (µL)"] < 10].shape[0])
    st.plotly_chart(px.bar(df, x="Type", title="📊 Global: Sample Count by Type"), use_container_width=True)
    df["Freezer"] = df["Storage Location"].apply(lambda x: x.split(" / ")[0])
    st.plotly_chart(px.pie(df, names="Freezer", title="🌍 Global: Freezer Distribution"), use_container_width=True)

# ✅ Final route logic
if "user" not in st.session_state or not st.session_state["user"]:
    show_login_page()
else:
    show_main_app()
