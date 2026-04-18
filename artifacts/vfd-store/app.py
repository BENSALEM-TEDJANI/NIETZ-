from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import os

app = Flask(__name__)

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

PRICE_MAP = {p["label"]: p["price"] for p in POWER_OPTIONS}

STATUSES = ["جديد", "تم الاتصال", "تم التأكيد", "تم الشحن"]

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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/order", methods=["GET", "POST"])
def order():
    global order_counter
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        phone    = request.form.get("phone", "").strip()
        wilaya   = request.form.get("wilaya", "").strip()
        power    = request.form.get("power", "").strip()
        quantity = request.form.get("quantity", "1").strip()

        if name and phone and wilaya and power:
            try:
                qty = max(1, int(quantity))
            except ValueError:
                qty = 1

            unit_price = PRICE_MAP.get(power, 0)
            total      = unit_price * qty
            order_id   = f"ORD-{order_counter}"
            order_counter += 1

            orders.append({
                "order_id":   order_id,
                "name":       name,
                "phone":      phone,
                "wilaya":     wilaya,
                "power":      power,
                "quantity":   qty,
                "unit_price": unit_price,
                "total":      total,
                "date":       datetime.now().strftime("%Y-%m-%d %H:%M"),
                "status":     "جديد",
            })
            return redirect(url_for("success", oid=order_id))

    return render_template("order.html", power_options=POWER_OPTIONS, wilayas=WILAYAS)


@app.route("/success")
def success():
    order_id = request.args.get("oid", "")
    return render_template("success.html", order_id=order_id)


@app.route("/admin")
def admin():
    search  = request.args.get("q", "").strip().upper()
    result  = list(reversed(orders))
    if search:
        result = [o for o in result if search in o["order_id"].upper()]
    return render_template("admin.html", orders=result, search=search, statuses=STATUSES)


@app.route("/admin/update-status", methods=["POST"])
def update_status():
    order_id   = request.form.get("order_id", "")
    new_status = request.form.get("status", "")
    for o in orders:
        if o["order_id"] == order_id:
            o["status"] = new_status
            break
    return redirect(url_for("admin"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
