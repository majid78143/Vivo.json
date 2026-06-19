import os
import json
import requests
import threading
import time
import random
import string
from datetime import datetime, timedelta
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, flash, abort, make_response)
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

from config import Config
from firebase_config import (init_firebase, get_firestore, verify_token,
                              FIREBASE_CLIENT_CONFIG)
from ads import ADS

app = Flask(__name__)
app.config.from_object(Config)

csrf = CSRFProtect(app)
limiter = Limiter(app=app, key_func=get_remote_address,
                  default_limits=["300 per day", "100 per hour"])

init_firebase()

# ─── Key rotation ────────────────────────────────────────────────────────────
_key_indices = {"imgbb": 0, "gemini": 0, "openai": 0}
_key_lock = threading.Lock()

def get_next_key(service):
    with _key_lock:
        keys = [k for k in app.config[f"{service.upper()}_KEYS"] if k]
        if not keys:
            return None
        idx = _key_indices[service] % len(keys)
        _key_indices[service] = (idx + 1) % len(keys)
        return keys[idx]

# ─── Helpers ─────────────────────────────────────────────────────────────────
def gen_id(n=12):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

def upload_to_imgbb(file_bytes, filename="image.jpg"):
    key = get_next_key("imgbb")
    if not key:
        return None
    try:
        import base64
        b64 = base64.b64encode(file_bytes).decode()
        r = requests.post("https://api.imgbb.com/1/upload",
                          data={"key": key, "image": b64, "name": filename},
                          timeout=15)
        data = r.json()
        if data.get("success"):
            return data["data"]["url"]
    except Exception as e:
        print(f"ImgBB upload error: {e}")
    return None

def send_telegram(text):
    token = app.config.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return
    try:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
        if chat_id:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat_id, "text": text}, timeout=5)
    except Exception:
        pass

def send_discord(text):
    webhook = app.config.get("DISCORD_WEBHOOK")
    if not webhook:
        return
    try:
        requests.post(webhook, json={"content": text}, timeout=5)
    except Exception:
        pass

# ─── Auth decorators ─────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            abort(403)
        return f(*args, **kwargs)
    return decorated

# ─── Context processor ───────────────────────────────────────────────────────
@app.context_processor
def inject_globals():
    db = get_firestore()
    settings = {}
    maintenance = False
    announcement = ""
    try:
        if db:
            s = db.collection("settings").document("global").get()
            if s.exists:
                settings = s.to_dict()
                maintenance = settings.get("maintenance_mode", False)
                announcement = settings.get("announcement", "")
    except Exception:
        pass
    return dict(
        firebase_config=FIREBASE_CLIENT_CONFIG,
        site_name=Config.SITE_NAME,
        logo_url=Config.LOGO_URL,
        favicon_url=Config.FAVICON_URL,
        theme={"primary": Config.THEME_PRIMARY, "secondary": Config.THEME_SECONDARY,
               "accent": Config.THEME_ACCENT, "bg": Config.THEME_BG},
        ads=ADS,
        current_user=session.get("user"),
        is_admin=session.get("is_admin", False),
        maintenance=maintenance,
        announcement=announcement,
        settings=settings,
        current_year=datetime.now().year,
    )

# ─── Maintenance check ───────────────────────────────────────────────────────
@app.before_request
def check_maintenance():
    allowed = ["static", "login", "admin_login", "admin_dashboard",
               "set_session", "health"]
    if request.endpoint and request.endpoint.split(".")[-1] in allowed:
        return
    db = get_firestore()
    try:
        if db:
            s = db.collection("settings").document("global").get()
            if s.exists and s.to_dict().get("maintenance_mode") and not session.get("is_admin"):
                return render_template("errors/maintenance.html"), 503
    except Exception:
        pass

# ─── Auth routes ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if session.get("user"):
        return redirect(url_for("home"))
    return redirect(url_for("login"))

@app.route("/login")
def login():
    if session.get("user"):
        return redirect(url_for("home"))
    return render_template("auth/login.html")

@app.route("/register")
def register():
    if session.get("user"):
        return redirect(url_for("home"))
    return render_template("auth/register.html")

@app.route("/forgot-password")
def forgot_password():
    return render_template("auth/forgot_password.html")

@app.route("/set-session", methods=["POST"])
@csrf.exempt
@limiter.limit("20 per minute")
def set_session():
    data = request.get_json()
    id_token = data.get("idToken")
    if not id_token:
        return jsonify({"error": "No token"}), 400
    decoded = verify_token(id_token)
    if not decoded:
        return jsonify({"error": "Invalid token"}), 401
    uid = decoded["uid"]
    email = decoded.get("email", "")
    name = decoded.get("name", email.split("@")[0])
    photo = decoded.get("picture", "")
    is_admin = email == app.config["ADMIN_EMAIL"]
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=30)
    session["user"] = {"uid": uid, "email": email, "name": name, "photo": photo}
    session["is_admin"] = is_admin
    db = get_firestore()
    if db:
        try:
            uref = db.collection("users").document(uid)
            udata = uref.get()
            if not udata.exists:
                uref.set({
                    "uid": uid, "email": email, "name": name, "photo": photo,
                    "created_at": datetime.utcnow().isoformat(),
                    "coins": 0, "vip": False, "banned": False,
                    "referral_code": gen_id(8), "referral_count": 0
                })
                send_discord(f"🆕 New user: {name} ({email})")
            else:
                uref.update({"last_login": datetime.utcnow().isoformat(),
                              "name": name, "photo": photo})
        except Exception as e:
            print(f"Firestore error: {e}")
    return jsonify({"success": True, "redirect": url_for("home")})

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─── Main pages ──────────────────────────────────────────────────────────────
@app.route("/home")
@login_required
def home():
    db = get_firestore()
    hero_banners, scroll_banners, featured_products, categories = [], [], [], []
    recent_winners, testimonials = [], []
    try:
        if db:
            hb = db.collection("hero_banners").where("active", "==", True).order_by("order").stream()
            hero_banners = [dict(d.to_dict(), id=d.id) for d in hb]
            sb = db.collection("scroll_banners").where("enabled", "==", True).stream()
            scroll_banners = [dict(d.to_dict(), id=d.id) for d in sb]
            fp = db.collection("products").where("featured", "==", True).limit(10).stream()
            featured_products = [dict(d.to_dict(), id=d.id) for d in fp]
            cats = db.collection("categories").stream()
            categories = [dict(d.to_dict(), id=d.id) for d in cats]
            rw = db.collection("winners").order_by("won_at", direction="DESCENDING").limit(5).stream()
            recent_winners = [dict(d.to_dict(), id=d.id) for d in rw]
            tm = db.collection("testimonials").where("approved", "==", True).limit(6).stream()
            testimonials = [dict(d.to_dict(), id=d.id) for d in tm]
    except Exception as e:
        print(f"Home fetch error: {e}")
    return render_template("pages/home.html", hero_banners=hero_banners,
                           scroll_banners=scroll_banners, featured_products=featured_products,
                           categories=categories, recent_winners=recent_winners,
                           testimonials=testimonials)

@app.route("/rewards")
@login_required
def rewards():
    return render_template("pages/rewards.html")

@app.route("/products")
@login_required
def products():
    db = get_firestore()
    prods, cat_filter = [], request.args.get("category", "")
    try:
        if db:
            q = db.collection("products")
            if cat_filter:
                q = q.where("category", "==", cat_filter)
            prods = [dict(d.to_dict(), id=d.id) for d in q.stream()]
    except Exception as e:
        print(e)
    return render_template("pages/products.html", products=prods, cat_filter=cat_filter)

@app.route("/product/<pid>")
@login_required
def product_detail(pid):
    db = get_firestore()
    product = None
    try:
        if db:
            d = db.collection("products").document(pid).get()
            if d.exists:
                product = dict(d.to_dict(), id=d.id)
    except Exception:
        pass
    if not product:
        abort(404)
    return render_template("pages/product_detail.html", product=product)

@app.route("/orders")
@login_required
def orders():
    db = get_firestore()
    user_orders = []
    try:
        if db:
            uid = session["user"]["uid"]
            ords = db.collection("orders").where("uid", "==", uid)\
                     .order_by("created_at", direction="DESCENDING").stream()
            user_orders = [dict(d.to_dict(), id=d.id) for d in ords]
    except Exception as e:
        print(e)
    return render_template("pages/orders.html", orders=user_orders)

@app.route("/order/<oid>")
@login_required
def order_detail(oid):
    db = get_firestore()
    order = None
    try:
        if db:
            d = db.collection("orders").document(oid).get()
            if d.exists:
                order = dict(d.to_dict(), id=d.id)
                if order.get("uid") != session["user"]["uid"] and not session.get("is_admin"):
                    abort(403)
    except Exception:
        pass
    if not order:
        abort(404)
    return render_template("pages/order_detail.html", order=order)

@app.route("/place-order", methods=["POST"])
@login_required
@limiter.limit("10 per hour")
def place_order():
    data = request.get_json()
    db = get_firestore()
    try:
        if db:
            uid = session["user"]["uid"]
            order_id = gen_id(10).upper()
            order_data = {
                "order_id": order_id, "uid": uid,
                "user_name": session["user"]["name"],
                "user_email": session["user"]["email"],
                "product_id": data.get("product_id"),
                "product_name": data.get("product_name"),
                "product_image": data.get("product_image"),
                "quantity": data.get("quantity", 1),
                "price": data.get("price"),
                "address": data.get("address", {}),
                "status": "pending",
                "tracking_code": "",
                "estimated_delivery": "",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            db.collection("orders").add(order_data)
            send_telegram(f"🛒 New Order #{order_id} by {session['user']['name']}")
            send_discord(f"🛒 New Order `#{order_id}` from **{session['user']['name']}**")
            return jsonify({"success": True, "order_id": order_id})
    except Exception as e:
        print(e)
    return jsonify({"error": "Failed to place order"}), 500

@app.route("/winners")
@login_required
def winners():
    db = get_firestore()
    all_winners = []
    try:
        if db:
            wn = db.collection("winners").order_by("won_at", direction="DESCENDING").limit(50).stream()
            all_winners = [dict(d.to_dict(), id=d.id) for d in wn]
    except Exception:
        pass
    return render_template("pages/winners.html", winners=all_winners)

@app.route("/coupons")
@login_required
def coupons():
    db = get_firestore()
    user_coupons = []
    try:
        if db:
            uid = session["user"]["uid"]
            cps = db.collection("user_coupons").where("uid", "==", uid)\
                    .where("used", "==", False).stream()
            user_coupons = [dict(d.to_dict(), id=d.id) for d in cps]
    except Exception:
        pass
    return render_template("pages/coupons.html", coupons=user_coupons)

@app.route("/mystery-boxes")
@login_required
def mystery_boxes():
    db = get_firestore()
    boxes = []
    try:
        if db:
            bx = db.collection("mystery_boxes").where("active", "==", True).stream()
            boxes = [dict(d.to_dict(), id=d.id) for d in bx]
    except Exception:
        pass
    return render_template("pages/mystery_boxes.html", boxes=boxes)

@app.route("/wishlist")
@login_required
def wishlist():
    db = get_firestore()
    items = []
    try:
        if db:
            uid = session["user"]["uid"]
            wl = db.collection("wishlists").where("uid", "==", uid).stream()
            items = [dict(d.to_dict(), id=d.id) for d in wl]
    except Exception:
        pass
    return render_template("pages/wishlist.html", items=items)

@app.route("/notifications")
@login_required
def notifications():
    db = get_firestore()
    notifs = []
    try:
        if db:
            uid = session["user"]["uid"]
            n = db.collection("notifications")\
                  .where("uid", "in", [uid, "all"])\
                  .order_by("created_at", direction="DESCENDING").limit(50).stream()
            notifs = [dict(d.to_dict(), id=d.id) for d in n]
    except Exception:
        pass
    return render_template("pages/notifications.html", notifications=notifs)

@app.route("/chat")
@login_required
def chat():
    db = get_firestore()
    messages = []
    try:
        if db:
            uid = session["user"]["uid"]
            msgs = db.collection("chats").document(uid)\
                     .collection("messages").order_by("sent_at").limit(100).stream()
            messages = [dict(d.to_dict(), id=d.id) for d in msgs]
    except Exception:
        pass
    return render_template("pages/chat.html", messages=messages)

@app.route("/chat/send", methods=["POST"])
@login_required
@limiter.limit("30 per minute")
def send_chat():
    db = get_firestore()
    try:
        uid = session["user"]["uid"]
        text = request.form.get("message", "")
        image_url = None
        if "image" in request.files:
            f = request.files["image"]
            if f and f.filename:
                image_url = upload_to_imgbb(f.read(), f.filename)
        if not text and not image_url:
            return jsonify({"error": "Empty message"}), 400
        msg = {
            "text": text, "image": image_url, "sender": "user",
            "sent_at": datetime.utcnow().isoformat(),
            "seen": False, "seen_at": None,
            "user_name": session["user"]["name"],
            "user_email": session["user"]["email"]
        }
        if db:
            db.collection("chats").document(uid).collection("messages").add(msg)
            db.collection("chats").document(uid).set({
                "uid": uid, "name": session["user"]["name"],
                "email": session["user"]["email"],
                "last_message": text or "[Image]",
                "last_at": datetime.utcnow().isoformat(),
                "unread_admin": True
            }, merge=True)
        return jsonify({"success": True, "message": msg})
    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@app.route("/profile")
@login_required
def profile():
    db = get_firestore()
    user_data = {}
    try:
        if db:
            uid = session["user"]["uid"]
            d = db.collection("users").document(uid).get()
            if d.exists:
                user_data = d.to_dict()
    except Exception:
        pass
    return render_template("pages/profile.html", user_data=user_data)

@app.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    db = get_firestore()
    try:
        uid = session["user"]["uid"]
        name = request.form.get("name", "")
        phone = request.form.get("phone", "")
        photo_url = session["user"].get("photo", "")
        if "photo" in request.files:
            f = request.files["photo"]
            if f and f.filename:
                url = upload_to_imgbb(f.read(), f.filename)
                if url:
                    photo_url = url
        if db:
            db.collection("users").document(uid).update({
                "name": name, "phone": phone, "photo": photo_url,
                "updated_at": datetime.utcnow().isoformat()
            })
            session["user"]["name"] = name
            session["user"]["photo"] = photo_url
        flash("Profile updated!", "success")
    except Exception as e:
        flash(f"Error: {e}", "error")
    return redirect(url_for("profile"))

@app.route("/settings")
@login_required
def settings():
    return render_template("pages/settings.html")

@app.route("/spin-wheel", methods=["POST"])
@login_required
@limiter.limit("5 per day")
def spin_wheel():
    db = get_firestore()
    try:
        uid = session["user"]["uid"]
        prizes = [10, 20, 50, 100, 5, 0, 200, 15]
        prize = random.choice(prizes)
        if db and prize > 0:
            db.collection("users").document(uid).update(
                {"coins": firestore_increment(prize)})
            db.collection("spin_history").add({
                "uid": uid, "prize": prize,
                "spun_at": datetime.utcnow().isoformat()
            })
        return jsonify({"success": True, "prize": prize})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def firestore_increment(n):
    try:
        from google.cloud.firestore_v1.transforms import SERVER_TIMESTAMP
        from firebase_admin import firestore as fstore
        return fstore.Increment(n)
    except Exception:
        return n

@app.route("/daily-reward", methods=["POST"])
@login_required
@limiter.limit("1 per day")
def daily_reward():
    db = get_firestore()
    try:
        uid = session["user"]["uid"]
        reward = random.randint(5, 50)
        if db:
            db.collection("users").document(uid).update(
                {"coins": firestore_increment(reward),
                 "last_daily": datetime.utcnow().isoformat()})
        return jsonify({"success": True, "reward": reward})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/scratch-card/<cid>", methods=["POST"])
@login_required
def scratch_card(cid):
    db = get_firestore()
    try:
        if db:
            uid = session["user"]["uid"]
            card = db.collection("scratch_cards").document(cid).get()
            if not card.exists:
                return jsonify({"error": "Not found"}), 404
            cdata = card.to_dict()
            if cdata.get("uid") != uid or cdata.get("scratched"):
                return jsonify({"error": "Invalid"}), 400
            prize = cdata.get("prize", 0)
            db.collection("scratch_cards").document(cid).update({"scratched": True})
            if prize > 0:
                db.collection("users").document(uid).update(
                    {"coins": firestore_increment(prize)})
            return jsonify({"success": True, "prize": prize})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/wishlist/toggle", methods=["POST"])
@login_required
def toggle_wishlist():
    db = get_firestore()
    try:
        uid = session["user"]["uid"]
        data = request.get_json()
        pid = data.get("product_id")
        if not db or not pid:
            return jsonify({"error": "Invalid"}), 400
        existing = db.collection("wishlists")\
                     .where("uid", "==", uid).where("product_id", "==", pid).stream()
        docs = list(existing)
        if docs:
            for d in docs:
                d.reference.delete()
            return jsonify({"success": True, "action": "removed"})
        else:
            db.collection("wishlists").add({
                "uid": uid, "product_id": pid,
                "added_at": datetime.utcnow().isoformat()
            })
            return jsonify({"success": True, "action": "added"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/coupon/apply", methods=["POST"])
@login_required
def apply_coupon():
    db = get_firestore()
    try:
        code = request.get_json().get("code", "").upper()
        if not db:
            return jsonify({"error": "Service unavailable"}), 500
        cps = db.collection("coupons").where("code", "==", code)\
                .where("active", "==", True).stream()
        coupon_list = list(cps)
        if not coupon_list:
            return jsonify({"error": "Invalid or expired coupon"}), 400
        coupon = coupon_list[0].to_dict()
        return jsonify({"success": True, "discount": coupon.get("discount", 0),
                        "type": coupon.get("type", "flat")})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Info pages ──────────────────────────────────────────────────────────────
@app.route("/faq")
def faq():
    return render_template("pages/faq.html")

@app.route("/about")
def about():
    return render_template("pages/about.html")

@app.route("/contact")
def contact():
    return render_template("pages/contact.html")

@app.route("/contact/submit", methods=["POST"])
@limiter.limit("5 per hour")
def contact_submit():
    db = get_firestore()
    try:
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")
        if db:
            db.collection("contact_messages").add({
                "name": name, "email": email, "message": message,
                "created_at": datetime.utcnow().isoformat(), "replied": False
            })
        send_discord(f"📩 Contact: **{name}** ({email})\n{message}")
        flash("Message sent successfully!", "success")
    except Exception:
        flash("Failed to send message.", "error")
    return redirect(url_for("contact"))

@app.route("/terms")
def terms():
    return render_template("pages/terms.html")

@app.route("/privacy")
def privacy():
    return render_template("pages/privacy.html")

@app.route("/shipping")
def shipping():
    return render_template("pages/shipping.html")

# ─── Admin panel ─────────────────────────────────────────────────────────────
@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_firestore()
    stats = {"users": 0, "orders": 0, "products": 0, "winners": 0}
    recent_orders = []
    try:
        if db:
            for key, col in [("users","users"),("orders","orders"),
                              ("products","products"),("winners","winners")]:
                docs = list(db.collection(col).stream())
                stats[key] = len(docs)
            ro = db.collection("orders").order_by("created_at", direction="DESCENDING").limit(5).stream()
            recent_orders = [dict(d.to_dict(), id=d.id) for d in ro]
    except Exception:
        pass
    return render_template("admin/dashboard.html", stats=stats, recent_orders=recent_orders)

@app.route("/admin/users")
@admin_required
def admin_users():
    db = get_firestore()
    users = []
    try:
        if db:
            users = [dict(d.to_dict(), id=d.id)
                     for d in db.collection("users").stream()]
    except Exception:
        pass
    return render_template("admin/users.html", users=users)

@app.route("/admin/users/<uid>/ban", methods=["POST"])
@admin_required
def admin_ban_user(uid):
    db = get_firestore()
    try:
        if db:
            data = request.get_json()
            db.collection("users").document(uid).update(
                {"banned": data.get("ban", True)})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/users/<uid>/vip", methods=["POST"])
@admin_required
def admin_vip_user(uid):
    db = get_firestore()
    try:
        if db:
            data = request.get_json()
            db.collection("users").document(uid).update(
                {"vip": data.get("vip", False)})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/orders")
@admin_required
def admin_orders():
    db = get_firestore()
    orders = []
    status_filter = request.args.get("status", "")
    try:
        if db:
            q = db.collection("orders").order_by("created_at", direction="DESCENDING")
            if status_filter:
                q = db.collection("orders").where("status", "==", status_filter)
            orders = [dict(d.to_dict(), id=d.id) for d in q.stream()]
    except Exception:
        pass
    return render_template("admin/orders.html", orders=orders, status_filter=status_filter)

@app.route("/admin/orders/<oid>/update", methods=["POST"])
@admin_required
def admin_update_order(oid):
    db = get_firestore()
    try:
        data = request.get_json()
        update_data = {"updated_at": datetime.utcnow().isoformat()}
        for field in ["status","tracking_code","estimated_delivery"]:
            if field in data:
                update_data[field] = data[field]
        if db:
            db.collection("orders").document(oid).update(update_data)
            if "status" in data:
                order = db.collection("orders").document(oid).get().to_dict()
                uid = order.get("uid")
                if uid:
                    db.collection("notifications").add({
                        "uid": uid, "title": "Order Update",
                        "body": f"Your order is now {data['status']}",
                        "created_at": datetime.utcnow().isoformat(), "read": False
                    })
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/products")
@admin_required
def admin_products():
    db = get_firestore()
    products = []
    try:
        if db:
            products = [dict(d.to_dict(), id=d.id)
                        for d in db.collection("products").stream()]
    except Exception:
        pass
    return render_template("admin/products.html", products=products)

@app.route("/admin/products/add", methods=["POST"])
@admin_required
def admin_add_product():
    db = get_firestore()
    try:
        name = request.form.get("name")
        price = float(request.form.get("price", 0))
        category = request.form.get("category", "")
        description = request.form.get("description", "")
        product_type = request.form.get("type", "physical")
        stock = int(request.form.get("stock", 0))
        featured = request.form.get("featured") == "on"
        image_url = ""
        if "image" in request.files:
            f = request.files["image"]
            if f and f.filename:
                image_url = upload_to_imgbb(f.read(), f.filename) or ""
        if db:
            db.collection("products").add({
                "name": name, "price": price, "category": category,
                "description": description, "type": product_type,
                "stock": stock, "featured": featured, "image": image_url,
                "created_at": datetime.utcnow().isoformat()
            })
        flash("Product added!", "success")
    except Exception as e:
        flash(f"Error: {e}", "error")
    return redirect(url_for("admin_products"))

@app.route("/admin/products/<pid>/delete", methods=["POST"])
@admin_required
def admin_delete_product(pid):
    db = get_firestore()
    try:
        if db:
            db.collection("products").document(pid).delete()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/chats")
@admin_required
def admin_chats():
    db = get_firestore()
    chat_rooms = []
    try:
        if db:
            chat_rooms = [dict(d.to_dict(), id=d.id)
                          for d in db.collection("chats").stream()]
    except Exception:
        pass
    return render_template("admin/chats.html", chat_rooms=chat_rooms)

@app.route("/admin/chats/<uid>")
@admin_required
def admin_chat_detail(uid):
    db = get_firestore()
    messages, chat_user = [], {}
    try:
        if db:
            msgs = db.collection("chats").document(uid)\
                     .collection("messages").order_by("sent_at").stream()
            messages = [dict(d.to_dict(), id=d.id) for d in msgs]
            for msg in messages:
                if msg.get("sender") == "user" and not msg.get("seen"):
                    db.collection("chats").document(uid)\
                      .collection("messages").document(msg["id"])\
                      .update({"seen": True, "seen_at": datetime.utcnow().isoformat()})
            cu = db.collection("chats").document(uid).get()
            if cu.exists:
                chat_user = cu.to_dict()
            db.collection("chats").document(uid).update({"unread_admin": False})
    except Exception:
        pass
    return render_template("admin/chat_detail.html", messages=messages,
                           chat_uid=uid, chat_user=chat_user)

@app.route("/admin/chats/<uid>/reply", methods=["POST"])
@admin_required
def admin_reply_chat(uid):
    db = get_firestore()
    try:
        text = request.form.get("message", "")
        image_url = None
        if "image" in request.files:
            f = request.files["image"]
            if f and f.filename:
                image_url = upload_to_imgbb(f.read(), f.filename)
        if not text and not image_url:
            return jsonify({"error": "Empty message"}), 400
        msg = {"text": text, "image": image_url, "sender": "admin",
               "sent_at": datetime.utcnow().isoformat(), "seen": False}
        if db:
            db.collection("chats").document(uid).collection("messages").add(msg)
            db.collection("chats").document(uid).update({
                "last_message": text or "[Image]",
                "last_at": datetime.utcnow().isoformat(), "unread_user": True
            })
            db.collection("notifications").add({
                "uid": uid, "title": "New Message",
                "body": "Admin replied to your message",
                "created_at": datetime.utcnow().isoformat(), "read": False
            })
        return jsonify({"success": True, "message": msg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/notifications")
@admin_required
def admin_notifications():
    db = get_firestore()
    notifs = []
    try:
        if db:
            notifs = [dict(d.to_dict(), id=d.id)
                      for d in db.collection("notifications")
                      .order_by("created_at", direction="DESCENDING").limit(50).stream()]
    except Exception:
        pass
    return render_template("admin/notifications.html", notifications=notifs)

@app.route("/admin/notifications/send", methods=["POST"])
@admin_required
def admin_send_notification():
    db = get_firestore()
    try:
        data = request.get_json()
        uid = data.get("uid", "all")
        title = data.get("title", "")
        body = data.get("body", "")
        if db:
            db.collection("notifications").add({
                "uid": uid, "title": title, "body": body,
                "created_at": datetime.utcnow().isoformat(), "read": False
            })
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/coupons")
@admin_required
def admin_coupons():
    db = get_firestore()
    coupons = []
    try:
        if db:
            coupons = [dict(d.to_dict(), id=d.id)
                       for d in db.collection("coupons").stream()]
    except Exception:
        pass
    return render_template("admin/coupons.html", coupons=coupons)

@app.route("/admin/coupons/add", methods=["POST"])
@admin_required
def admin_add_coupon():
    db = get_firestore()
    try:
        data = request.get_json()
        if db:
            db.collection("coupons").add({
                "code": data.get("code","").upper(),
                "discount": float(data.get("discount", 0)),
                "type": data.get("type", "flat"),
                "active": True,
                "max_uses": int(data.get("max_uses", 100)),
                "used_count": 0,
                "created_at": datetime.utcnow().isoformat()
            })
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/coupons/<cid>/toggle", methods=["POST"])
@admin_required
def admin_toggle_coupon(cid):
    db = get_firestore()
    try:
        if db:
            doc = db.collection("coupons").document(cid).get()
            current = doc.to_dict().get("active", True)
            db.collection("coupons").document(cid).update({"active": not current})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/winners")
@admin_required
def admin_winners():
    db = get_firestore()
    winners = []
    try:
        if db:
            winners = [dict(d.to_dict(), id=d.id)
                       for d in db.collection("winners")
                       .order_by("won_at", direction="DESCENDING").stream()]
    except Exception:
        pass
    return render_template("admin/winners.html", winners=winners)

@app.route("/admin/winners/add", methods=["POST"])
@admin_required
def admin_add_winner():
    db = get_firestore()
    try:
        data = request.get_json()
        photo = data.get("photo","")
        if db:
            db.collection("winners").add({
                "name": data.get("name",""),
                "prize": data.get("prize",""),
                "photo": photo,
                "won_at": datetime.utcnow().isoformat(),
                "approved": True
            })
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/hero-banners")
@admin_required
def admin_hero_banners():
    db = get_firestore()
    banners = []
    try:
        if db:
            banners = [dict(d.to_dict(), id=d.id)
                       for d in db.collection("hero_banners").order_by("order").stream()]
    except Exception:
        pass
    return render_template("admin/hero_banners.html", banners=banners)

@app.route("/admin/hero-banners/add", methods=["POST"])
@admin_required
def admin_add_hero_banner():
    db = get_firestore()
    try:
        image_url = ""
        if "image" in request.files:
            f = request.files["image"]
            if f and f.filename:
                image_url = upload_to_imgbb(f.read(), f.filename) or ""
        if db:
            db.collection("hero_banners").add({
                "title": request.form.get("title",""),
                "subtitle": request.form.get("subtitle",""),
                "btn_text": request.form.get("btn_text",""),
                "btn_link": request.form.get("btn_link",""),
                "image": image_url,
                "active": request.form.get("active") == "on",
                "order": int(request.form.get("order", 0)),
                "created_at": datetime.utcnow().isoformat()
            })
        flash("Banner added!", "success")
    except Exception as e:
        flash(str(e), "error")
    return redirect(url_for("admin_hero_banners"))

@app.route("/admin/hero-banners/<bid>/delete", methods=["POST"])
@admin_required
def admin_delete_hero_banner(bid):
    db = get_firestore()
    try:
        if db:
            db.collection("hero_banners").document(bid).delete()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/hero-banners/<bid>/toggle", methods=["POST"])
@admin_required
def admin_toggle_hero_banner(bid):
    db = get_firestore()
    try:
        if db:
            doc = db.collection("hero_banners").document(bid).get()
            current = doc.to_dict().get("active", True)
            db.collection("hero_banners").document(bid).update({"active": not current})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/scroll-banners")
@admin_required
def admin_scroll_banners():
    db = get_firestore()
    banners = []
    try:
        if db:
            banners = [dict(d.to_dict(), id=d.id)
                       for d in db.collection("scroll_banners").stream()]
    except Exception:
        pass
    return render_template("admin/scroll_banners.html", banners=banners)

@app.route("/admin/scroll-banners/add", methods=["POST"])
@admin_required
def admin_add_scroll_banner():
    db = get_firestore()
    try:
        data = request.get_json()
        if db:
            db.collection("scroll_banners").add({
                "text": data.get("text",""),
                "color": data.get("color","#A78BFA"),
                "enabled": True,
                "created_at": datetime.utcnow().isoformat()
            })
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/scroll-banners/<bid>/toggle", methods=["POST"])
@admin_required
def admin_toggle_scroll_banner(bid):
    db = get_firestore()
    try:
        if db:
            doc = db.collection("scroll_banners").document(bid).get()
            current = doc.to_dict().get("enabled", True)
            db.collection("scroll_banners").document(bid).update({"enabled": not current})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/scroll-banners/<bid>/delete", methods=["POST"])
@admin_required
def admin_delete_scroll_banner(bid):
    db = get_firestore()
    try:
        if db:
            db.collection("scroll_banners").document(bid).delete()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/api-config")
@admin_required
def admin_api_config():
    return render_template("admin/api_config.html",
                           imgbb_keys=app.config["IMGBB_KEYS"],
                           gemini_keys=app.config["GEMINI_KEYS"],
                           openai_keys=app.config["OPENAI_KEYS"],
                           telegram_token=app.config["TELEGRAM_BOT_TOKEN"],
                           discord_webhook=app.config["DISCORD_WEBHOOK"])

@app.route("/admin/settings")
@admin_required
def admin_settings():
    db = get_firestore()
    site_settings = {}
    try:
        if db:
            s = db.collection("settings").document("global").get()
            if s.exists:
                site_settings = s.to_dict()
    except Exception:
        pass
    return render_template("admin/settings.html", site_settings=site_settings)

@app.route("/admin/settings/update", methods=["POST"])
@admin_required
def admin_update_settings():
    db = get_firestore()
    try:
        data = request.get_json()
        if db:
            db.collection("settings").document("global").set(data, merge=True)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/admin/analytics")
@admin_required
def admin_analytics():
    db = get_firestore()
    data = {"signups_today": 0, "orders_today": 0, "revenue_today": 0,
            "active_users": 0}
    try:
        if db:
            today = datetime.utcnow().date().isoformat()
            users = list(db.collection("users").stream())
            data["active_users"] = len(users)
            data["signups_today"] = sum(
                1 for u in users if u.to_dict().get("created_at","").startswith(today))
            ords = list(db.collection("orders").stream())
            today_ords = [o.to_dict() for o in ords
                          if o.to_dict().get("created_at","").startswith(today)]
            data["orders_today"] = len(today_ords)
            data["revenue_today"] = sum(
                float(o.get("price", 0)) for o in today_ords)
    except Exception:
        pass
    return render_template("admin/analytics.html", analytics=data)

@app.route("/admin/login")
def admin_login():
    return redirect(url_for("login"))

@app.route("/health")
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})

# ─── API: upload image ────────────────────────────────────────────────────────
@app.route("/api/upload-image", methods=["POST"])
@login_required
@limiter.limit("20 per hour")
def api_upload_image():
    if "image" not in request.files:
        return jsonify({"error": "No image"}), 400
    f = request.files["image"]
    url = upload_to_imgbb(f.read(), f.filename)
    if url:
        return jsonify({"success": True, "url": url})
    return jsonify({"error": "Upload failed"}), 500

@app.route("/api/notifications/read/<nid>", methods=["POST"])
@login_required
def mark_notification_read(nid):
    db = get_firestore()
    try:
        if db:
            db.collection("notifications").document(nid).update({"read": True})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Error handlers ──────────────────────────────────────────────────────────
@app.errorhandler(403)
def forbidden(e):
    return render_template("errors/403.html"), 403

@app.errorhandler(404)
def not_found(e):
    return render_template("errors/404.html"), 404

@app.errorhandler(429)
def rate_limited(e):
    return render_template("errors/429.html"), 429

@app.errorhandler(500)
def server_error(e):
    return render_template("errors/500.html"), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))
