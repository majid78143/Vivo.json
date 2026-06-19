import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dreamdrop-secret-key-2024')
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@dreamdrop.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    SITE_NAME = 'DreamDrop'
    LOGO_URL = 'https://i.ibb.co/placeholder/logo.png'
    FAVICON_URL = 'https://i.ibb.co/placeholder/favicon.ico'
    THEME_PRIMARY = '#A78BFA'
    THEME_SECONDARY = '#F9A8D4'
    THEME_ACCENT = '#67E8F9'
    THEME_BG = '#F5F3FF'
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    RATELIMIT_DEFAULT = '200 per day;50 per hour'
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

    FIREBASE_CONFIG = {
        "apiKey": "AIzaSyCuZDyri0F0ky2sHxFO-p2OKvEB2sQfihw",
        "authDomain": "dreamdrop-3ca3d.firebaseapp.com",
        "databaseURL": "https://dreamdrop-3ca3d-default-rtdb.firebaseio.com",
        "projectId": "dreamdrop-3ca3d",
        "storageBucket": "dreamdrop-3ca3d.firebasestorage.app",
        "messagingSenderId": "882827368473",
        "appId": "1:882827368473:web:bf146e6c9f5db32edbb288",
        "measurementId": "G-Z6B3CZZRC9"
    }

    IMGBB_KEYS = [
        os.environ.get('IMGBB_KEY_1', ''),
        os.environ.get('IMGBB_KEY_2', ''),
        os.environ.get('IMGBB_KEY_3', ''),
        os.environ.get('IMGBB_KEY_4', ''),
        os.environ.get('IMGBB_KEY_5', ''),
        os.environ.get('IMGBB_KEY_6', ''),
        os.environ.get('IMGBB_KEY_7', ''),
        os.environ.get('IMGBB_KEY_8', ''),
        os.environ.get('IMGBB_KEY_9', ''),
        os.environ.get('IMGBB_KEY_10', ''),
    ]

    GEMINI_KEYS = [
        os.environ.get('GEMINI_KEY_1', ''),
        os.environ.get('GEMINI_KEY_2', ''),
        os.environ.get('GEMINI_KEY_3', ''),
        os.environ.get('GEMINI_KEY_4', ''),
        os.environ.get('GEMINI_KEY_5', ''),
        os.environ.get('GEMINI_KEY_6', ''),
        os.environ.get('GEMINI_KEY_7', ''),
        os.environ.get('GEMINI_KEY_8', ''),
        os.environ.get('GEMINI_KEY_9', ''),
        os.environ.get('GEMINI_KEY_10', ''),
    ]

    OPENAI_KEYS = [
        os.environ.get('OPENAI_KEY_1', ''),
        os.environ.get('OPENAI_KEY_2', ''),
        os.environ.get('OPENAI_KEY_3', ''),
        os.environ.get('OPENAI_KEY_4', ''),
        os.environ.get('OPENAI_KEY_5', ''),
        os.environ.get('OPENAI_KEY_6', ''),
        os.environ.get('OPENAI_KEY_7', ''),
        os.environ.get('OPENAI_KEY_8', ''),
        os.environ.get('OPENAI_KEY_9', ''),
        os.environ.get('OPENAI_KEY_10', ''),
    ]

    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK', '')
