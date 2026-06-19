# 🌟 DreamDrop

**Premium Mobile-First Flask Web Application**

Shop. Earn. Win. — Built with Firebase, Python Flask, and premium UI.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your values:
```bash
cp .env.example .env
```

### 3. Firebase Setup
- Go to [Firebase Console](https://console.firebase.google.com)
- Enable **Authentication** (Email/Password + Google)
- Enable **Firestore Database**
- Enable **Realtime Database**
- Enable **Storage**
- Download `serviceAccountKey.json` and place in root, OR
- Set `FIREBASE_SERVICE_ACCOUNT` env var with the JSON string

### 4. Run Locally
```bash
python app.py
```
App runs at `http://localhost:5000`

---

## 🌐 Deploy to Render

1. Push code to GitHub
2. Connect repo to [Render.com](https://render.com)
3. Set environment variables:
   - `SECRET_KEY` — Random secure string
   - `ADMIN_EMAIL` — Your admin email
   - `ADMIN_PASSWORD` — Admin password (for admin panel check)
   - `FIREBASE_SERVICE_ACCOUNT` — Firebase service account JSON string
4. Deploy!

---

## 🔑 Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Flask secret key |
| `ADMIN_EMAIL` | Admin email address |
| `ADMIN_PASSWORD` | Admin login password |
| `FIREBASE_SERVICE_ACCOUNT` | Firebase admin SDK JSON |
| `IMGBB_KEY_1` to `_10` | ImgBB API keys (auto-rotated) |
| `GEMINI_KEY_1` to `_10` | Gemini API keys |
| `OPENAI_KEY_1` to `_10` | OpenAI API keys |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Telegram chat ID |
| `DISCORD_WEBHOOK` | Discord webhook URL |

---

## 📁 Project Structure

```
dreamdrop/
├── app.py                  # Main Flask application
├── config.py               # Configuration
├── firebase_config.py      # Firebase setup
├── ads.py                  # Ad scripts
├── requirements.txt        # Dependencies
├── Procfile                # Render/Heroku deploy
├── render.yaml             # Render config
├── templates/
│   ├── base.html           # Base template
│   ├── auth/               # Login, Register, Forgot PW
│   ├── pages/              # All user pages
│   ├── admin/              # Admin panel pages
│   └── errors/             # Error pages
└── static/
    ├── css/main.css        # Premium styles
    ├── js/main.js          # Main JS
    ├── js/firebase-auth.js # Firebase auth
    ├── manifest.json       # PWA manifest
    └── sw.js               # Service Worker
```

---

## 🎯 Features

- ✅ Google Login & Email/Password Auth
- ✅ Email Verification & Password Reset
- ✅ Firestore & Realtime Database integration
- ✅ Hero Banner with auto-slide & touch swipe
- ✅ Infinite scrolling announcement banner
- ✅ Products (Physical & Digital)
- ✅ Complete Order System with tracking
- ✅ WhatsApp-style Chat with admin reply
- ✅ Rewards: Spin Wheel, Daily Reward, Scratch Cards
- ✅ Mystery Boxes
- ✅ Coupons & Wishlist
- ✅ Winners Hall of Fame
- ✅ Push Notifications
- ✅ Admin Panel (13 sections)
- ✅ 10 ImgBB/Gemini/OpenAI keys with auto-rotation
- ✅ Telegram & Discord alerts
- ✅ PWA (installable)
- ✅ Dark Mode
- ✅ Adsterra Ads integrated
- ✅ CSRF Protection, Rate Limiting
- ✅ Maintenance Mode
- ✅ Glassmorphism UI, Confetti, Ripple effects

---

## 🛡️ Admin Panel

Access at `/admin` — requires login with `ADMIN_EMAIL`.

Sections: Dashboard · Users · Orders · Products · Chats · Notifications · Coupons · Winners · Hero Banners · Scroll Banners · API Config · Settings · Analytics

---

*Made with ❤️ — DreamDrop v1.0.0*
