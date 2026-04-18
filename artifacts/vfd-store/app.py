from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "nietz-secret-key-2025")

DB_PATH = os.path.join(os.path.dirname(__file__), "nietz.db")

# ─── In-memory orders ────────────────────────────────────────────────────────
orders = []
order_counter = 1001

POWER_OPTIONS = [
    {"label": "0.75 kW", "price": 18000},
    {"label": "1.5 kW",  "price": 22000},
    {"label": "2.2 kW",  "price": 28000},
    {"label": "3.7 kW",  "price": 35000},
    {"label": "5.5 kW",  "price": 45000},
    {"label": "7.5 kW",  "price": 55000},
    {"label": "11 kW",   "price": 75000},
    {"label": "15 kW",   "price": 95000},
    {"label": "18.5 kW", "price": 115000},
    {"label": "22 kW",   "price": 135000},
    {"label": "30 kW",   "price": 165000},
    {"label": "37 kW",   "price": 195000},
    {"label": "45 kW",   "price": 230000},
    {"label": "55 kW",   "price": 270000},
]
PRICE_MAP  = {p["label"]: p["price"] for p in POWER_OPTIONS}
STATUSES   = ["جديد", "تم الاتصال", "تم التأكيد", "تم الشحن", "تم الاستلام"]

WILAYAS = [
    "أدرار", "الشلف", "الأغواط", "أم البواقي", "باتنة", "بجاية", "بسكرة",
    "بشار", "البليدة", "البويرة", "تمنراست", "تبسة", "تلمسان", "تيارت",
    "تيزي وزو", "الجزائر", "الجلفة", "جيجل", "سطيف", "سعيدة", "سكيكدة",
    "سيدي بلعباس", "عنابة", "قالمة", "قسنطينة", "المدية", "مستغانم",
    "المسيلة", "معسكر", "ورقلة", "وهران", "البيض", "إليزي", "برج بوعريريج",
    "بومرداس", "الطارف", "تندوف", "تيسمسيلت", "الوادي", "خنشلة",
    "سوق أهراس", "تيبازة", "ميلة", "عين الدفلى", "النعامة", "عين تموشنت",
    "غرداية", "غليزان", "تيميمون", "برج باجي مختار", "أولاد جلال",
    "بني عباس", "إن صالح", "إن قزام", "توقرت", "جانت", "المغير", "المنيعة",
    "عين بسام", "بريكة", "الخروب", "عين الباردة", "أميزور",
    "مقرة", "عين أزال", "تبلبالة", "سيدي خالد", "السوقر", "عين فكرون"
]

# ─── Database helpers ─────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    UNIQUE NOT NULL,
                password TEXT    NOT NULL,
                role     TEXT    NOT NULL DEFAULT 'employee'
            )
        """)
        # Create default admin if no users exist
        cur = conn.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO users (username, password, role) VALUES (?,?,?)",
                ("admin", generate_password_hash("admin123"), "admin")
            )
        conn.commit()

# ─── Auth decorators ──────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("ليس لديك صلاحية للوصول إلى هذه الصفحة", "error")
            return redirect(url_for("admin"))
        return f(*args, **kwargs)
    return decorated

# ─── Public routes ────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/order", methods=["GET", "POST"])
def order():
    global order_counter
    if request.method == "POST":
        name   = request.form.get("name", "").strip()
        phone  = request.form.get("phone", "").strip()
        wilaya = request.form.get("wilaya", "").strip()

        powers     = request.form.getlist("power[]")
        quantities = request.form.getlist("qty[]")

        if name and phone and wilaya and powers:
            items = []
            total = 0
            for pw, qt in zip(powers, quantities):
                pw = pw.strip()
                if not pw:
                    continue
                try:
                    qty = max(1, int(qt))
                except ValueError:
                    qty = 1
                unit_price = PRICE_MAP.get(pw, 0)
                subtotal   = unit_price * qty
                total     += subtotal
                items.append({
                    "power":      pw,
                    "quantity":   qty,
                    "unit_price": unit_price,
                    "subtotal":   subtotal,
                })

            if items:
                order_id = f"ORD-{order_counter}"
                order_counter += 1
                orders.append({
                    "order_id": order_id,
                    "name":     name,
                    "phone":    phone,
                    "wilaya":   wilaya,
                    "items":    items,
                    "total":    total,
                    "date":     datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "status":   "جديد",
                })
                return redirect(url_for("success", oid=order_id))

    return render_template("order.html", power_options=POWER_OPTIONS, wilayas=WILAYAS)

@app.route("/success")
def success():
    return render_template("success.html", order_id=request.args.get("oid", ""))

# ─── Auth routes ──────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("admin"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
        if user and check_password_hash(user["password"], password):
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            session["role"]     = user["role"]
            return redirect(url_for("admin"))
        error = "اسم المستخدم أو كلمة المرور غير صحيحة"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ─── Admin routes ─────────────────────────────────────────────────────────────
@app.route("/admin")
@login_required
def admin():
    search = request.args.get("q", "").strip().upper()
    result = list(reversed(orders))
    if search:
        result = [o for o in result if search in o["order_id"].upper()]
    return render_template(
        "admin.html",
        orders=result,
        search=search,
        statuses=STATUSES,
        role=session.get("role"),
        username=session.get("username"),
    )

@app.route("/admin/update-status", methods=["POST"])
@login_required
def update_status():
    order_id   = request.form.get("order_id", "")
    new_status = request.form.get("status", "")
    for o in orders:
        if o["order_id"] == order_id:
            o["status"] = new_status
            break
    return redirect(url_for("admin"))

# ─── Users management (admin only) ───────────────────────────────────────────
@app.route("/admin/users")
@admin_required
def admin_users():
    with get_db() as conn:
        users = conn.execute("SELECT id, username, role FROM users ORDER BY id").fetchall()
    return render_template(
        "admin_users.html",
        users=users,
        role=session.get("role"),
        username=session.get("username"),
    )

@app.route("/admin/users/add", methods=["POST"])
@admin_required
def add_user():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    role     = request.form.get("role", "employee")
    if username and password and role in ("admin", "employee"):
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO users (username, password, role) VALUES (?,?,?)",
                    (username, generate_password_hash(password), role)
                )
                conn.commit()
            flash(f"تم إضافة المستخدم '{username}' بنجاح", "success")
        except sqlite3.IntegrityError:
            flash("اسم المستخدم موجود مسبقاً", "error")
    else:
        flash("يرجى ملء جميع الحقول بشكل صحيح", "error")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/edit/<int:uid>", methods=["POST"])
@admin_required
def edit_user(uid):
    new_role     = request.form.get("role", "")
    new_password = request.form.get("password", "").strip()
    with get_db() as conn:
        if new_password:
            conn.execute(
                "UPDATE users SET role=?, password=? WHERE id=?",
                (new_role, generate_password_hash(new_password), uid)
            )
        else:
            conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, uid))
        conn.commit()
    flash("تم تحديث المستخدم بنجاح", "success")
    return redirect(url_for("admin_users"))

@app.route("/admin/users/delete/<int:uid>", methods=["POST"])
@admin_required
def delete_user(uid):
    if uid == session.get("user_id"):
        flash("لا يمكنك حذف حسابك الحالي", "error")
        return redirect(url_for("admin_users"))
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
        conn.commit()
    flash("تم حذف المستخدم بنجاح", "success")
    return redirect(url_for("admin_users"))

# ─── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
