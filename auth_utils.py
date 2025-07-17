# auth_utils.py
import streamlit as st
from firebase_admin import auth
from firebase_config import db

def login_user(email, password):
    try:
        user = auth.get_user_by_email(email)
        st.session_state["user"] = {
            "email": user.email,
            "uid": user.uid,
        }
        # Optional: Load role from Firestore
        role_ref = db.collection("users").document(user.uid)
        role_doc = role_ref.get()
        if role_doc.exists:
            st.session_state["user"]["role"] = role_doc.to_dict().get("role", "Technician")
        else:
            st.session_state["user"]["role"] = "Technician"
        return True
    except Exception as e:
        st.error(f"Login failed: {e}")
        return False

def logout_user():
    if "user" in st.session_state:
        del st.session_state["user"]
        st.success("You’ve been logged out.")
