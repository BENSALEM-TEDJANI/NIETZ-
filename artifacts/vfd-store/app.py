from flask import Flask, render_template, request, redirect, url_for
import os

app = Flask(__name__)

orders = []

POWER_OPTIONS = [
    "0.75 kW", "1.5 kW", "2.2 kW", "3.7 kW", "5.5 kW",
    "7.5 kW", "11 kW", "15 kW", "18.5 kW", "22 kW",
    "30 kW", "37 kW", "45 kW", "55 kW"
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
    "بني عباس", "إن صالح", "إن قزام", "توقرت", "جانت", "المغير", "المنيعة"
]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/order", methods=["GET", "POST"])
def order():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        wilaya = request.form.get("wilaya", "").strip()
        power = request.form.get("power", "").strip()

        if name and phone and wilaya and power:
            orders.append({
                "name": name,
                "phone": phone,
                "wilaya": wilaya,
                "power": power
            })
            return redirect(url_for("success"))

    return render_template("order.html", power_options=POWER_OPTIONS, wilayas=WILAYAS)


@app.route("/success")
def success():
    return render_template("success.html")


@app.route("/admin")
def admin():
    return render_template("admin.html", orders=orders)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
