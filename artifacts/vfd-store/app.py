from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import sqlite3
import os
import urllib.request
import urllib.parse
import threading

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "nietz-secret-key-2025")

WHATSAPP_PHONE  = os.environ.get("WHATSAPP_PHONE",  "213562617736")
WHATSAPP_APIKEY = os.environ.get("WHATSAPP_APIKEY", "")

def send_whatsapp(message: str):
    if not WHATSAPP_APIKEY:
        return
    def _send():
        try:
            params = urllib.parse.urlencode({
                "phone":  WHATSAPP_PHONE,
                "text":   message,
                "apikey": WHATSAPP_APIKEY,
            })
            url = f"https://api.callmebot.com/whatsapp.php?{params}"
            urllib.request.urlopen(url, timeout=10)
        except Exception:
            pass
    threading.Thread(target=_send, daemon=True).start()

DB_PATH = os.path.join(os.path.dirname(__file__), "nietz.db")

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

COMMUNES = {
    "أدرار": ["أدرار", "رقان", "أولف", "زاوية كنتة", "فنوغيل", "تيمياوين", "تيت", "أقبلي", "بودة", "تامست", "سالي", "أنزاو"],
    "الشلف": ["الشلف", "تنس", "أم الدروع", "بوقادير", "تاجنة", "بني حواء", "الهرانة", "وادي الفضة", "أبو الحسن", "الكريمة", "مصدق", "بريرة", "الحجاج", "الخطاب", "سيدي عكاشة", "بنايرية"],
    "الأغواط": ["الأغواط", "حاسي الرمل", "قلتة سيدي سعد", "آفلو", "حاسي دلاعة", "سيدي مخلوف", "برج خنيفيس", "بريدة", "عين سيدي علي"],
    "أم البواقي": ["أم البواقي", "عين البيضاء", "عين مليلة", "عين فكرون", "سيقوس", "المسكيانة", "عين كشرة", "عين الزيتون", "فكيرينة", "ثليجان", "بلزمة", "وادي نيني"],
    "باتنة": ["باتنة", "عين التوتة", "مروانة", "أريس", "رأس العيون", "بريكة", "تكوت", "نقاوس", "قصبة", "تيمقاد", "ثنية العابد", "بومية", "آزيل عبد القادر", "بيطام", "واد الشعبة"],
    "بجاية": ["بجاية", "أكفادو", "خراطة", "سيدي عيش", "فينيق", "تيقسابت", "أميزور", "ضرمون", "أقبو", "الفلاي", "الكمان", "تيشي", "بني مليكيش", "مالبو", "أوزلاقن"],
    "بسكرة": ["بسكرة", "سيدي خالد", "طولقة", "أوماش", "عين الناقة", "زريبة الوادي", "لوطاية", "فوغالة", "خنقة سيدي ناجي", "أولاد جلال", "رأس الميعاد", "جمورة"],
    "بشار": ["بشار", "عين الصفراء", "تبلبالة", "إقلي", "محاضر", "القنادسة", "بن عمر", "طاغيت", "مشرية"],
    "البليدة": ["البليدة", "الأربعاء", "بوفاريك", "بوعينان", "شعبة اللوز", "عين الحمام", "مفتاح", "الصومعة", "الشريعة", "قرواو", "موزاية", "مصفى"],
    "البويرة": ["البويرة", "عين بسام", "سور الغزلان", "أعين الحمام", "القبة", "ملاكو", "بشلول", "أولاد راشد", "آت لزيز", "العجيبة", "ذراع القايد"],
    "تمنراست": ["تمنراست", "إن قزام", "إن غار", "عين صالح", "إدلس", "إن غزام"],
    "تبسة": ["تبسة", "الشريعة", "بكارية", "شريعة", "النقرين", "العوينات", "قريقر", "أم علي", "حمام النبائل", "الحويجبات", "مرسط"],
    "تلمسان": ["تلمسان", "وجدة", "مغنية", "سيدي بلعباس", "الغزوات", "رمشي", "سبدو", "بني صاف", "بني سنوس", "بني بوسعيد", "عين تالة", "أولاد ميمون", "فلاوسن", "بنساكن"],
    "تيارت": ["تيارت", "سوق أهراس", "عين الدهب", "السوقر", "قصر الشلالة", "تخمرت", "مدروسة", "عين كرمس", "مهدية", "وادي ليلي", "سبعين"],
    "تيزي وزو": ["تيزي وزو", "عزازقة", "دراع بن خدة", "بوغني", "بومرداس", "ذراع الميزان", "ولايزة", "آيت محمود", "لربعاء نايت ايراتن", "إيفرحونن", "آيت عيسى ميمون", "يطافن", "بوجيلة"],
    "الجزائر": ["باب الوادي", "القصبة", "الحراش", "برج البحري", "رويبة", "الرغاية", "الدار البيضاء", "بوزريعة", "المحمدية", "بن عكنون", "الأبيار", "حيدرة", "الكاليتوس", "سيدي عبد الله", "بئر مراد رايس", "درارية"],
    "الجلفة": ["الجلفة", "مسعد", "عين وسارة", "السبسب", "العش", "بيرين", "بوسعادة", "سيدي لعجل", "زكار", "دار الشيوخ"],
    "جيجل": ["جيجل", "الميلية", "الطاهير", "تاكسنة", "شقفة", "خير الدين", "زيامة منصورية", "سيدي معروف", "سطارة"],
    "سطيف": ["سطيف", "عين أزال", "عين ولمان", "بوقاعة", "بئر العرش", "عين لقصير", "عروسية", "بني عزيز", "أولاد سيدي احمد", "مزلوق", "بلاعة"],
    "سعيدة": ["سعيدة", "عين الحجر", "تيرين", "سيدي امحمد بن علي", "حوش دبيش", "يوب", "سيدي بوبكر"],
    "سكيكدة": ["سكيكدة", "رمضان جمال", "الحروش", "عزابة", "بن عزوز", "تمالوس", "زيغود يوسف", "عين قشرة", "كركرة", "القل"],
    "سيدي بلعباس": ["سيدي بلعباس", "تلاغ", "معسكر", "مرحوم", "سيدي داود", "تاودموت", "حاسي زهانة", "سيدي خالد"],
    "عنابة": ["عنابة", "سرايدي", "برحال", "شطايبي", "الحجار", "عين الباردة", "عين البرج"],
    "قالمة": ["قالمة", "بلخير", "بوشقوف", "حمام دباغ", "بوحمدان", "عين المخلوف", "هيليوبوليس"],
    "قسنطينة": ["قسنطينة", "الخروب", "عين عبيد", "ديدوش مراد", "حامة بوزيان", "زيغود يوسف", "إبن زياد"],
    "المدية": ["المدية", "بني سليمان", "كار", "قصر البخاري", "بوغزول", "ثنية الحد", "عين بوسيف", "ازريريق"],
    "مستغانم": ["مستغانم", "عين تدلس", "المشرية", "عشعاشة", "مظغرة", "خضرة"],
    "المسيلة": ["المسيلة", "بوسعادة", "مقرة", "سيدي عيسى", "الحمامة", "أولاد دراج", "عين الحجل", "سيدي امحمد"],
    "معسكر": ["معسكر", "سيق", "زمالة الأمير عبد القادر", "تزيزاوت", "البرج", "عين فارس"],
    "ورقلة": ["ورقلة", "تقرت", "حاسي مسعود", "النقوسة", "المنقر", "روابح", "بلدة اميل", "سيدي خويلد"],
    "وهران": ["وهران", "أرزيو", "بطيوة", "مرسى الكبير", "وادي تليلات", "سيدي الشحمي", "البيت وعلام", "حاسي بونيف"],
    "البيض": ["البيض", "بريزينة", "النعامة", "قصيبة وثامير", "بوقطب", "الشقيق"],
    "إليزي": ["إليزي", "جانت", "إن أميناس", "دبدب"],
    "برج بوعريريج": ["برج بوعريريج", "رأس الوادي", "المنصورة", "برج زمورة", "قصر البخاري"],
    "بومرداس": ["بومرداس", "الرويبة", "تمزريت", "ذراع بن خدة", "براقي", "قورصو", "إسي علي", "الأربعاء"],
    "الطارف": ["الطارف", "الشعف", "بوحجار", "الذرعان", "عين الأبيض", "قالة", "الشافية"],
    "تندوف": ["تندوف"],
    "تيسمسيلت": ["تيسمسيلت", "ثنية الحد", "أماغر", "برج الأمير عبد القادر", "لرجام"],
    "الوادي": ["الوادي", "الرباح", "بن قشة", "كوينين", "قمار", "تالة العقاد", "حاسي خليفة", "أولاد دراج"],
    "خنشلة": ["خنشلة", "بغاي", "مصارة", "جلال", "طاولة"],
    "سوق أهراس": ["سوق أهراس", "سدراتة", "مداوروش", "تاورة", "عين الزانة"],
    "تيبازة": ["تيبازة", "القليعة", "بواسماعيل", "شرشال", "دواودة", "الصومعة", "فوكة", "سيدي راشد", "مراد"],
    "ميلة": ["ميلة", "فرجيوة", "شلغوم العيد", "تسعة", "سيدي مروان", "أحمد راشدي"],
    "عين الدفلى": ["عين الدفلى", "خميس مليانة", "العطاف", "مليانة", "بوميدفع", "تاشتة زقاغة"],
    "النعامة": ["النعامة", "مشرية", "عين الصفراء", "جنين بورزق", "تيوت", "صفيصيفة"],
    "عين تموشنت": ["عين تموشنت", "بني صاف", "الأغلال", "سيدي بن عدة", "عقب الليل", "تارقا"],
    "غرداية": ["غرداية", "متليلي", "بريان", "بونورة", "القرارة", "بريان", "المنيعة", "زلفانة"],
    "غليزان": ["غليزان", "رلزان", "جيدل", "سيدي خطاب", "واد رهيو", "واد جمعة"],
    "تيميمون": ["تيميمون", "أولف", "زاوية كنتة", "رقان", "ملس"],
    "برج باجي مختار": ["برج باجي مختار", "تيميمون"],
    "أولاد جلال": ["أولاد جلال", "سيدي خالد", "البسباس"],
    "بني عباس": ["بني عباس", "القنادسة", "تيمودة"],
    "إن صالح": ["إن صالح", "إن قزام"],
    "إن قزام": ["إن قزام"],
    "توقرت": ["توقرت", "تقرت", "المگارين", "الزاوية العابدية"],
    "جانت": ["جانت", "إيليزي"],
    "المغير": ["المغير", "أولاد رابح", "سيدي خليل"],
    "المنيعة": ["المنيعة", "حاسي القارة"],
    "عين بسام": ["عين بسام", "البويرة", "حاجرة"],
    "بريكة": ["بريكة", "آريس", "لازرو"],
    "الخروب": ["الخروب", "قسنطينة", "ديدوش مراد"],
    "عين الباردة": ["عين الباردة", "عنابة", "الحجار"],
    "أميزور": ["أميزور", "بجاية", "أقبو"],
    "مقرة": ["مقرة", "المسيلة", "سيدي عيسى"],
    "عين أزال": ["عين أزال", "سطيف", "بوقاعة"],
    "تبلبالة": ["تبلبالة", "بشار", "إقلي"],
    "سيدي خالد": ["سيدي خالد", "بسكرة", "طولقة"],
    "السوقر": ["السوقر", "تيارت", "فرندة"],
    "عين فكرون": ["عين فكرون", "أم البواقي", "عين مليلة"],
}

# ─── Database helpers ──────────────────────────────────────────────────────────
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT    UNIQUE NOT NULL,
                name     TEXT    NOT NULL,
                phone    TEXT    NOT NULL,
                wilaya   TEXT    NOT NULL,
                total    INTEGER NOT NULL DEFAULT 0,
                date     TEXT    NOT NULL,
                status   TEXT    NOT NULL DEFAULT 'جديد'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id   TEXT    NOT NULL,
                power      TEXT    NOT NULL,
                quantity   INTEGER NOT NULL DEFAULT 1,
                unit_price INTEGER NOT NULL DEFAULT 0,
                subtotal   INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (order_id) REFERENCES orders(order_id)
            )
        """)
        # Migration: add commune column if missing
        try:
            conn.execute("ALTER TABLE orders ADD COLUMN commune TEXT DEFAULT ''")
            conn.commit()
        except Exception:
            pass

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

# ─── Orders DB helpers ─────────────────────────────────────────────────────────
def create_order(name, phone, wilaya, commune, items, total):
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO orders (order_id, name, phone, wilaya, commune, total, date, status) VALUES (?,?,?,?,?,?,?,?)",
            ("PENDING", name, phone, wilaya, commune, total, date_str, "جديد")
        )
        row_id = cur.lastrowid
        order_id = f"ORD-{1000 + row_id}"
        conn.execute("UPDATE orders SET order_id=? WHERE id=?", (order_id, row_id))
        for item in items:
            conn.execute(
                "INSERT INTO order_items (order_id, power, quantity, unit_price, subtotal) VALUES (?,?,?,?,?)",
                (order_id, item["power"], item["quantity"], item["unit_price"], item["subtotal"])
            )
        conn.commit()
    return order_id

def _row_to_order(row, items_rows):
    return {
        "order_id": row["order_id"],
        "name":     row["name"],
        "phone":    row["phone"],
        "wilaya":   row["wilaya"],
        "commune":  row["commune"] if "commune" in row.keys() else "",
        "total":    row["total"],
        "date":     row["date"],
        "status":   row["status"],
        "products": [
            {
                "power":      r["power"],
                "quantity":   r["quantity"],
                "unit_price": r["unit_price"],
                "subtotal":   r["subtotal"],
            }
            for r in items_rows
        ],
    }

def get_all_orders():
    with get_db() as conn:
        order_rows = conn.execute(
            "SELECT * FROM orders ORDER BY id DESC"
        ).fetchall()
        items_map = {}
        if order_rows:
            placeholders = ",".join("?" for _ in order_rows)
            ids = [r["order_id"] for r in order_rows]
            item_rows = conn.execute(
                f"SELECT * FROM order_items WHERE order_id IN ({placeholders})",
                ids
            ).fetchall()
            for ir in item_rows:
                items_map.setdefault(ir["order_id"], []).append(ir)
    return [_row_to_order(r, items_map.get(r["order_id"], [])) for r in order_rows]

def update_order_status_db(order_id, new_status):
    with get_db() as conn:
        conn.execute(
            "UPDATE orders SET status=? WHERE order_id=?",
            (new_status, order_id)
        )
        conn.commit()

def get_order_counts():
    now = datetime.now()
    old_cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%d %H:%M")
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        old   = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE date < ?", (old_cutoff,)
        ).fetchone()[0]
        counts = {"all": total, "old": old}
        for s in STATUSES:
            counts[s] = conn.execute(
                "SELECT COUNT(*) FROM orders WHERE status=?", (s,)
            ).fetchone()[0]
    return counts

# ─── Auth decorators ───────────────────────────────────────────────────────────
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

# ─── Public routes ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/products")
def products():
    prods = get_products()
    import json
    return render_template(
        "products.html",
        products=prods,
        wilayas=WILAYAS,
        communes_json=json.dumps(COMMUNES, ensure_ascii=False),
    )

@app.route("/order", methods=["GET", "POST"])
def order():
    if request.method == "GET":
        return redirect(url_for("products"))

    power_options = get_products()
    price_map     = {p["label"]: p["price"] for p in power_options}

    name      = request.form.get("name", "").strip()
    phone     = request.form.get("phone", "").strip()
    wilaya    = request.form.get("wilaya", "").strip()
    commune   = request.form.get("commune", "").strip()
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
            order_id = create_order(name, phone, wilaya, commune, items, total)
            items_text = "\n".join(
                f"  - {it['power']} x{it['quantity']} = {it['subtotal']:,} dz"
                for it in items
            )
            msg = (
                f"طلب جديد #{order_id}\n"
                f"الاسم: {name}\n"
                f"الهاتف: {phone}\n"
                f"الولاية: {wilaya}" + (f" / {commune}" if commune else "") + "\n"
                f"المنتجات:\n{items_text}\n"
                f"الاجمالي: {total:,} دج"
            )
            send_whatsapp(msg)
            return redirect(url_for("success", oid=order_id))

    return redirect(url_for("products"))

@app.route("/success")
def success():
    return render_template("success.html", order_id=request.args.get("oid", ""))

# ─── Auth routes ───────────────────────────────────────────────────────────────
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

# ─── Admin orders ──────────────────────────────────────────────────────────────
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

    result = get_all_orders()

    if q:
        result = [o for o in result if
                  q in o.get("order_id", "").lower() or
                  q in o.get("name",     "").lower() or
                  q in o.get("phone",    "").lower() or
                  q in o.get("wilaya",   "").lower() or
                  q in o.get("commune",  "").lower() or
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

    counts = get_order_counts()

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
    if order_id and new_status in STATUSES:
        update_order_status_db(order_id, new_status)
    return redirect(url_for("admin", tab=tab))

# ─── Admin products ────────────────────────────────────────────────────────────
@app.route("/admin/products")
@admin_required
def admin_products():
    prods = get_products()
    return render_template(
        "admin_products.html",
        products=prods,
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

# ─── Users management ──────────────────────────────────────────────────────────
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

# ─── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
