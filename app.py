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

# ✅ Set page config
st.set_page_config(page_title="Smart Biospecimen Tracker", layout="wide", initial_sidebar_state="collapsed")

# ✅ Check if user is logged in
if "user" not in st.session_state or not st.session_state["user"]:
    st.title("🔐 Login to Smart Biospecimen Tracker")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login", key="login_button"):
        login_user(email, password)

else:
    # ✅ Show logged-in app
    user = st.session_state["user"]
    st.sidebar.markdown(f"👤 Logged in as: `{user['email']}`")

    # ✅ Show user role if available
    role = user.get("role", "Technician")
    st.sidebar.markdown(f"🛡 Role: `{role}`")

    # ✅ Logout button with unique key
    if st.sidebar.button("🚪 Logout", key="logout_button"):
        logout_user()
        st.experimental_rerun()

    # 👉 Main app begins here
    st.title("🧬 Smart Biospecimen Lifecycle Tracker")
    st.subheader("📦 Register New Sample")

    # ✅ Log function (MUST be inside the `else` block)
    def log_sample_activity(sample_id, action, details):
        log_entry = {
            "action": action,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        db.collection("samples").document(sample_id).collection("activity_log").add(log_entry)

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
import streamlit.components.v1 as components

# Inject CSS for responsive sidebar collapse on small devices
st.markdown("""
    <style>
        @media (max-width: 768px) {
            [data-testid="stSidebar"] {
                display: none;
            }
        }
    </style>
""", unsafe_allow_html=True)

st.set_page_config(
    page_title="Smart Biospecimen Tracker",
    layout="wide",
    initial_sidebar_state="collapsed"
)
st.title("🧬 Smart Biospecimen Lifecycle Tracker")
st.subheader("📦 Register New Sample")

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
    # ✅ Save to Firebase
    db.collection("samples").document(sample_id).set({
        "sample_id": sample_id,
        "type": sample_type,
        "volume": volume,
        "location": location,
        "expiry": expiry_date.strftime("%Y-%m-%d"),
        "created_at": datetime.now().isoformat()
    })
    st.success(f"✅ Sample {sample_id} registered successfully!")

    # ✅ Log activity
    try:
        log_sample_activity(
            sample_id,
            action="register_sample",
            details=f"Sample registered with volume {volume} µL at {location}."
        )
        st.info("📌 Activity logged.")
    except Exception as e:
        st.error(f"❌ Logging failed: {e}")

    # -------------------------------------
# 📜 View Activity Log (New Section)
# -------------------------------------
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

    # ✅ Generate QR Code
    qr_data = f"ID: {sample_id}\nType: {sample_type}\nLocation: {location}\nExpiry: {expiry_date.strftime('%Y-%m-%d')}"
    qr_img = qrcode.make(qr_data).convert("RGB")  # Ensures proper PIL Image

    # ✅ Convert QR to bytes for PNG download
    buffer = io.BytesIO()
    qr_img.save(buffer, format="PNG")
    qr_bytes = buffer.getvalue()

    # ✅ Display QR
    st.subheader("🧬 Sample QR Code")
    st.image(qr_bytes, caption="Scan to retrieve sample info", use_container_width=True)

    # ✅ PNG Download
    b64 = base64.b64encode(qr_bytes).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="sample_{sample_id}.png">📥 Download QR Code as PNG</a>'
    st.markdown(href, unsafe_allow_html=True)

    # ✅ PDF Label
    pdf_buffer = generate_pdf(
        sample_id,
        sample_type,
        volume,
        location,
        expiry_date.strftime('%Y-%m-%d'),
        qr_img
    )
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

# -----------------------------
# 👤 Logged-in User + Logout Button
# -----------------------------
if "user" in st.session_state:
    st.sidebar.markdown(f"👤 Logged in as: `{st.session_state['user']['email']}`")
    if st.sidebar.button("🚪 Logout", key="logout_button"):
        logout_user()
        st.experimental_rerun()

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
# -----------------------------
# 📈 Analytics Summary (Filtered)
# -----------------------------
st.markdown("### 📊 Filtered Sample Analytics")

total_samples = len(filtered_df)
expiring_soon = filtered_df[filtered_df["⚠️ Alert"].str.contains("Expiring Soon")].shape[0]
low_volume = filtered_df[filtered_df["⚠️ Alert"].str.contains("Low Volume")].shape[0]

col1, col2, col3 = st.columns(3)
col1.metric("📦 Total Samples", total_samples)
col2.metric("⏰ Expiring Soon", expiring_soon)
col3.metric("🧪 Low Volume", low_volume)

import plotly.express as px

# 📊 Samples by Type (Filtered)
type_chart = px.bar(filtered_df, x="Type", title="🧬 Sample Count by Type")
st.plotly_chart(type_chart, use_container_width=True)

# 🧊 Freezer Distribution (Filtered)
filtered_df["Freezer"] = filtered_df["Storage Location"].apply(lambda x: x.split(" / ")[0])
freezer_chart = px.pie(filtered_df, names="Freezer", title="🗃️ Freezer Distribution")
st.plotly_chart(freezer_chart, use_container_width=True)

# ----------------------------------------
# 📊 Global Analytics Dashboard (Unfiltered)
# ----------------------------------------
# -----------------------------
# 🌐 Global Analytics Summary (unfiltered)
# -----------------------------
st.markdown("### 🌐 Global Sample Analytics (All Data)")

# Ensure 'Expiry Date' is in datetime format
df["Expiry Date"] = pd.to_datetime(df["Expiry Date"])

global_total = len(df)
global_expiring = df[df["Expiry Date"] <= (datetime.today() + timedelta(days=7))]
global_low_vol = df[df["Volume (µL)"] < 10]

col1, col2, col3 = st.columns(3)
col1.metric("🧮 Total Samples", global_total)
col2.metric("⚠️ Expiring Soon (7 days)", len(global_expiring))
col3.metric("🧪 Low Volume (<10 µL)", len(global_low_vol))

# 📊 Global Samples by Type
global_type_chart = px.bar(df, x="Type", title="📊 Global: Sample Count by Type")
st.plotly_chart(global_type_chart, use_container_width=True)

# 🧊 Global Freezer Distribution
df["Freezer"] = df["Storage Location"].apply(lambda x: x.split(" / ")[0])
global_freezer_chart = px.pie(df, names="Freezer", title="🌍 Global: Freezer Distribution")
st.plotly_chart(global_freezer_chart, use_container_width=True)


