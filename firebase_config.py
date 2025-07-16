# firebase_config.py
import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# Load Firebase credentials from Render environment variable
firebase_creds = json.loads(os.environ["FIREBASE_KEY_JSON"])
cred = credentials.Certificate(firebase_creds)
firebase_admin.initialize_app(cred)

# Initialize Firestore
db = firestore.client()
