import firebase_admin
from firebase_admin import credentials, firestore, auth, storage, db
import os
import json

_firebase_app = None
_firestore_client = None

def init_firebase():
    global _firebase_app, _firestore_client
    if _firebase_app:
        return _firebase_app
    try:
        service_account_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT', '')
        if service_account_json:
            cred_dict = json.loads(service_account_json)
            cred = credentials.Certificate(cred_dict)
        elif os.path.exists('serviceAccountKey.json'):
            cred = credentials.Certificate('serviceAccountKey.json')
        else:
            cred = credentials.ApplicationDefault()

        _firebase_app = firebase_admin.initialize_app(cred, {
            'storageBucket': 'dreamdrop-3ca3d.firebasestorage.app',
            'databaseURL': 'https://dreamdrop-3ca3d-default-rtdb.firebaseio.com'
        })
        _firestore_client = firestore.client()
    except Exception as e:
        print(f"Firebase Admin init warning: {e}")
        _firebase_app = None
        _firestore_client = None
    return _firebase_app

def get_firestore():
    global _firestore_client
    if not _firestore_client:
        init_firebase()
    return _firestore_client

def verify_token(id_token):
    try:
        decoded = auth.verify_id_token(id_token)
        return decoded
    except Exception as e:
        return None

def get_user_by_email(email):
    try:
        return auth.get_user_by_email(email)
    except Exception:
        return None

FIREBASE_CLIENT_CONFIG = {
    "apiKey": "AIzaSyCuZDyri0F0ky2sHxFO-p2OKvEB2sQfihw",
    "authDomain": "dreamdrop-3ca3d.firebaseapp.com",
    "databaseURL": "https://dreamdrop-3ca3d-default-rtdb.firebaseio.com",
    "projectId": "dreamdrop-3ca3d",
    "storageBucket": "dreamdrop-3ca3d.firebasestorage.app",
    "messagingSenderId": "882827368473",
    "appId": "1:882827368473:web:bf146e6c9f5db32edbb288",
    "measurementId": "G-Z6B3CZZRC9"
}
