from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import sqlite3
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "nietz-secret-key-2025")

DB_PATH = os.path.join(os.path.dirname(__file__), "nietz.db")

# ─── In-memory orders ────────────────────────────────────────────────────────
orders = []
order_counter = 1001

STATUSES = ["جديد", "تم الاتصال", "تم التأكيد", "تم الشحن", "تم الاستلام"]

DEFAULT_PRODUCTS = [
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                label      TEXT    UNIQUE NOT NULL,
                price      INTEGER NOT NULL DEFAULT 0,
                sort_order INTEGER NOT NULL DEFAULT 0
            )
        """)
        cur = conn.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO users (username, password, role) VALUES (?,?,?)",
                ("admin", generate_password_hash("admin123"), "admin")
            )
        cur2 = conn.execute("SELECT COUNT(*) FROM products")
        if cur2.fetchone()[0] == 0:
            for i, p in enumerate(DEFAULT_PRODUCTS):
                conn.execute(
                    "INSERT INTO products (label, price, sort_order) VALUES (?,?,?)",
                    (p["label"], p["price"], i)
                )
        conn.commit()

def get_products():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, label, price FROM products ORDER BY sort_order, id"
        ).fetchall()
    return [{"id": r["id"], "label": r["label"], "price": r["price"]} for r in rows]

def get_price_map():
    return {p["label"]: p["price"] for p in get_products()}

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

@app.route("/products")
def products():
    prods = get_products()
    return render_template("products.html", products=prods)

@app.route("/order", methods=["GET", "POST"])
def order():
    global order_counter
    power_options = get_products()
    price_map     = {p["label"]: p["price"] for p in power_options}

    if request.method == "POST":
        name      = request.form.get("name", "").strip()
        phone     = request.form.get("phone", "").strip()
        wilaya    = request.form.get("wilaya", "").strip()
        powers    = request.form.getlist("power[]")
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
                unit_price = price_map.get(pw, 0)
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
                    "products": items,
                    "total":    total,
                    "date":     datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "status":   "جديد",
                })
                return redirect(url_for("success", oid=order_id))

    return render_template("order.html", power_options=power_options, wilayas=WILAYAS)

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

# ─── Admin orders ─────────────────────────────────────────────────────────────
@app.route("/admin")
@app.route("/admin/orders")
@login_required
def admin():
    q           = request.args.get("q", "").strip().lower()
    tab         = request.args.get("tab", "all")
    date_filter = request.args.get("df", "")
    now         = datetime.now()
    old_cutoff  = now - timedelta(days=7)

    def parse_date(d):
        try:
            return datetime.strptime(d, "%Y-%m-%d %H:%M")
        except Exception:
            return now

    result = list(reversed(orders))

    if q:
        result = [o for o in result if
                  q in o.get("order_id", "").lower() or
                  q in o.get("name",     "").lower() or
                  q in o.get("phone",    "").lower() or
                  q in o.get("wilaya",   "").lower() or
                  q in o.get("date",     "").lower()]

    if tab == "old":
        result = [o for o in result if parse_date(o["date"]) < old_cutoff]
    elif tab in STATUSES:
        result = [o for o in result if o.get("status") == tab]

    if date_filter == "today":
        today = now.strftime("%Y-%m-%d")
        result = [o for o in result if o.get("date", "").startswith(today)]
    elif date_filter == "week":
        week_ago = now - timedelta(days=7)
        result = [o for o in result if parse_date(o["date"]) >= week_ago]
    elif date_filter == "month":
        month_ago = now - timedelta(days=30)
        result = [o for o in result if parse_date(o["date"]) >= month_ago]

    counts = {"all": len(orders), "old": 0}
    for s in STATUSES:
        counts[s] = sum(1 for o in orders if o.get("status") == s)
    counts["old"] = sum(1 for o in orders if parse_date(o["date"]) < old_cutoff)

    return render_template(
        "admin.html",
        orders=result,
        search=q,
        statuses=STATUSES,
        tab=tab,
        date_filter=date_filter,
        counts=counts,
        role=session.get("role"),
        username=session.get("username"),
    )

@app.route("/admin/update-status", methods=["POST"])
@login_required
def update_status():
    order_id   = request.form.get("order_id", "")
    new_status = request.form.get("status", "")
    tab        = request.form.get("tab", "all")
    for o in orders:
        if o["order_id"] == order_id:
            o["status"] = new_status
            break
    return redirect(url_for("admin", tab=tab))

# ─── Admin products ───────────────────────────────────────────────────────────
@app.route("/admin/products")
@admin_required
def admin_products():
    products = get_products()
    return render_template(
        "admin_products.html",
        products=products,
        role=session.get("role"),
        username=session.get("username"),
    )

@app.route("/admin/products/add", methods=["POST"])
@admin_required
def add_product():
    label = request.form.get("label", "").strip()
    price = request.form.get("price", "0").strip()
    if label:
        try:
            price_val = max(0, int(price))
        except ValueError:
            price_val = 0
        try:
            with get_db() as conn:
                max_order = conn.execute("SELECT MAX(sort_order) FROM products").fetchone()[0] or 0
                conn.execute(
                    "INSERT INTO products (label, price, sort_order) VALUES (?,?,?)",
                    (label, price_val, max_order + 1)
                )
                conn.commit()
            flash(f"تم إضافة المنتج '{label}' بنجاح", "success")
        except sqlite3.IntegrityError:
            flash("هذا المنتج موجود مسبقاً", "error")
    else:
        flash("يرجى إدخال اسم المنتج", "error")
    return redirect(url_for("admin_products"))

@app.route("/admin/products/edit/<int:pid>", methods=["POST"])
@admin_required
def edit_product(pid):
    label = request.form.get("label", "").strip()
    price = request.form.get("price", "0").strip()
    if label:
        try:
            price_val = max(0, int(price))
        except ValueError:
            price_val = 0
        with get_db() as conn:
            conn.execute(
                "UPDATE products SET label=?, price=? WHERE id=?",
                (label, price_val, pid)
            )
            conn.commit()
        flash("تم تحديث المنتج بنجاح", "success")
    else:
        flash("يرجى إدخال اسم المنتج", "error")
    return redirect(url_for("admin_products"))

@app.route("/admin/products/delete/<int:pid>", methods=["POST"])
@admin_required
def delete_product(pid):
    with get_db() as conn:
        conn.execute("DELETE FROM products WHERE id=?", (pid,))
        conn.commit()
    flash("تم حذف المنتج بنجاح", "success")
    return redirect(url_for("admin_products"))

# ─── Users management ─────────────────────────────────────────────────────────
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
