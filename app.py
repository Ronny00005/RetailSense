import psycopg2
from psycopg2.extras  import RealDictCursor
import io
from flask import send_file
from flask import Flask, request, jsonify, redirect, url_for, render_template, session
from statsmodels.tsa.statespace.sarimax import SARIMAX

import json

import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import pandas as pd
app = Flask(__name__, static_folder="static")  


app.secret_key = "super_secret_key"

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"csv"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
@app.route("/favicon.ico")
def favicon():
    return "", 204

def load_user_csv(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT csv_path FROM users WHERE id = %s", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if not result or not result[0]:
        return None

    csv_path = result[0]

    if not os.path.exists(csv_path):
        print("CSV FILE NOT FOUND:", csv_path)
        return None

    df = pd.read_csv(csv_path)

    if "date" not in df.columns:
        raise Exception("CSV must contain a 'date' column")

    df["date"] = pd.to_datetime(df["date"])
    return df

def process_sales_data(df):
    # Clean columns
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Ensure date
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Derived metrics
    if "cost_price" not in df.columns:
        df["cost_price"] = df["selling_price"] * 0.7  # fallback

    df["profit"] = (df["selling_price"] - df["cost_price"]) * df["quantity"]

    df["sales"] = df["selling_price"] * df["quantity"]
   
    return df

# -------------------- DATABASE --------------------


def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is NOT set")
    return psycopg2.connect(db_url)

    









# -------------------- HELPERS --------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# -------------------- ROUTES --------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/faqs")
def faqs():
    return render_template("faqs.html")

# -------------------- SIGNUP --------------------


@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False}), 400

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO users (full_name, email, mobile, password)
            VALUES (%s, %s, %s, %s)
            """,
            (
                data["full_name"],
                data["email"],
                data["mobile"],
                generate_password_hash(data["password"])
            )
        )

        conn.commit()
        return jsonify({"success": True})

    except psycopg2.errors.UniqueViolation:
        return jsonify({"success": False, "message": "Email already exists"}), 409

    except Exception as e:
        print("SIGNUP ERROR:", e)
        return jsonify({"success": False}), 500

    finally:
        if conn:
            conn.close()




# -------------------- LOGIN --------------------


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False}), 400

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email = %s", (data["email"],))
    user = cur.fetchone()

    conn.close()

    if not user or not check_password_hash(user[4], data["password"]):
        return jsonify({"success": False}), 401

    session["user_id"] = user[0]
    session["user_name"] = user[1]

    return jsonify({
        "success": True,
        "user_id": user[0],
        "name": user[1],
        "csv_uploaded": user[5]
    })
# -------------------- CSV UPLOAD --------------------
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user_id" not in session:
        return jsonify({"success": False, "redirect": url_for("index")}), 401

    if request.method == "GET":
        return render_template("upload.html")

    # ---------- POST ----------
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"})

    file = request.files["file"]

    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"success": False, "message": "Invalid file"})

    filename = secure_filename(f"user_{session['user_id']}.csv")
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
    "UPDATE users SET csv_uploaded = %s, csv_path = %s WHERE id = %s",
    (True, filepath, session["user_id"]))

    conn.commit()
    conn.close()

    return jsonify({
    "success": True,
    "redirect": url_for("dashboard")
})



# -------------------- DASHBOARD --------------------



# -------------------- LOGOUT --------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# -------------------- RUN --------------------


    
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("index"))

    # ---------------- LOAD CSV ----------------
    df = load_user_csv(session["user_id"])
    if df is None:
        return redirect(url_for("upload"))

    df = process_sales_data(df)

    # ---------------- OVERALL KPIs ----------------
    total_sales = round(df["sales"].sum(), 2)
    net_profit = round(df["profit"].sum(), 2)
    avg_profit = round(df["profit"].mean(), 2)

    top_item = (
        df.groupby("item_name")["quantity"]
        .sum()
        .idxmax()
    )

    # ---------------- TOP 5 ITEMS ----------------
    top_5_df = (
        df.groupby("item_name")
        .agg(
            units_sold=("quantity", "sum"),
            revenue=("sales", "sum")
        )
        .sort_values("units_sold", ascending=False)
        .head(5)
        .reset_index()
    )

    top_5_items = [
        {
            "name": row["item_name"],
            "units_sold": int(row["units_sold"]),
            "revenue": round(row["revenue"], 2)
        }
        for _, row in top_5_df.iterrows()
    ]

    # ---------------- CATEGORY ANALYSIS ----------------
    category_sales = (
        df.groupby("category")["sales"]
        .sum()
        .sort_values(ascending=False)
    )

    total_category_sales = category_sales.sum()

    top_3_categories = [
        {
            "name": cat,
            "revenue": round(val, 2),
            "percentage": round((val / total_category_sales) * 100, 2)
        }
        for cat, val in category_sales.head(3).items()
    ]

    bottom_3_categories = [
        {
            "name": cat,
            "revenue": round(val, 2),
            "percentage": round((val / total_category_sales) * 100, 2)
        }
        for cat, val in category_sales.tail(3).items()
    ]
# ---------------- USER INFO ----------------
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT email FROM users WHERE id = %s",
        (session["user_id"],)
    )
    user_email = cur.fetchone()[0]
    conn.close()

    return render_template(
        "dashboard.html",
        user_name=session["user_name"],
        user_email=user_email,
        user_role="Retail Analyst",

        total_sales=total_sales,
        net_profit=net_profit,
        avg_profit=avg_profit,
        top_item=top_item,

        top_5_items=top_5_items,
        top_3_categories=top_3_categories,
        bottom_3_categories=bottom_3_categories,
    
    )
@app.route("/api/datewise-report", methods=["POST"])
def datewise_report():
    if "user_id" not in session:
        return jsonify({"success": False}), 401

    data = request.get_json()
    from_date = data.get("from_date")
    to_date = data.get("to_date")

    df = load_user_csv(session["user_id"])
    df = process_sales_data(df)

    filtered_df = df[
        (df["date"] >= from_date) &
        (df["date"] <= to_date)
    ]

    if filtered_df.empty:
        return jsonify({
            "success": True,
            "sales": 0,
            "profit": 0,
            "top_product": "-",
            "worst_product": "-"
        })

    #  CONVERT TO PYTHON TYPES
    sales = float(filtered_df["sales"].sum())
    profit = float(filtered_df["profit"].sum())

    top_product = (
        filtered_df.groupby("item_name")["sales"]
        .sum()
        .idxmax()
    )

    worst_product = (
        filtered_df.groupby("item_name")["sales"]
        .sum()
        .idxmin()
    )

    return jsonify({
        "success": True,
        "sales": round(sales, 2),
        "profit": round(profit, 2),
        "top_product": str(top_product),
        "worst_product": str(worst_product)
    })
@app.route("/api/category-charts")
def category_charts():
    if "user_id" not in session:
        return jsonify({"success": False}), 401

    df = load_user_csv(session["user_id"])
    df = process_sales_data(df)

    category_sales = (
        df.groupby("category")["sales"]
        .sum()
        .sort_values(ascending=False)
    )

    return jsonify({
        "success": True,
        "labels": list(category_sales.index),
        "values": [float(v) for v in category_sales.values]
    })
@app.route("/api/monthly-sales")
def monthly_sales():
    if "user_id" not in session:
        return jsonify({"success": False}), 401

    df = load_user_csv(session["user_id"])
    df = process_sales_data(df)

    monthly = (
        df.set_index("date")
        .resample("ME")["sales"]
        .sum()
    )

    return jsonify({
        "success": True,
        "labels": [d.strftime("%b") for d in monthly.index],
        "values": [float(v) for v in monthly.values]
    })

@app.route("/download/excel", methods=["POST"])
def download_excel():
    if "user_id" not in session:
        return jsonify({"success": False}), 401

    data = request.get_json()
    from_date = data.get("from_date")
    to_date = data.get("to_date")

    df = load_user_csv(session["user_id"])
    df = process_sales_data(df)

    filtered_df = df[
        (df["date"] >= from_date) &
        (df["date"] <= to_date)
    ]

    if filtered_df.empty:
        return jsonify({"success": False, "message": "No data available"}), 400

    output = io.BytesIO()
    filtered_df.to_excel(output, index=False)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="datewise_report.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.errorhandler(Exception)
def handle_exception(e):
    print("UNHANDLED ERROR:", e)
    return jsonify({"error": str(e)}), 500
@app.route("/api/future-forecast")
def future_forecast():
    if "user_id" not in session:
        return jsonify({"success": False}), 401

    try:
        df = load_user_csv(session["user_id"])
        df = process_sales_data(df)

        if "sales" not in df.columns:
            return jsonify({
                "success": False,
                "message": "Sales column missing in CSV"
            })

        # ---------------- DAILY SALES ----------------
        daily_sales = (
            df.set_index("date")
            .resample("D")["sales"]
            .sum()
        )

        # Limit to last 365 days for performance
        daily_sales = daily_sales.tail(365)

        if len(daily_sales) < 60:
            return jsonify({
                "success": False,
                "message": "Not enough data for forecast"
            })

        # ---------------- SARIMAX (WEEKLY SEASONALITY) ----------------
        model = SARIMAX(
            daily_sales,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 7),  # ✅ weekly pattern
            enforce_stationarity=False,
            enforce_invertibility=False
        )

        results = model.fit(disp=False)

        # ---------------- FORECAST NEXT 365 DAYS ----------------
        forecast_days = 365
        forecast = results.get_forecast(steps=forecast_days)
        daily_forecast = forecast.predicted_mean.clip(lower=0)

        # ---------------- CONVERT DAILY → MONTHLY ----------------
        monthly_forecast = (
            daily_forecast
            .resample("ME")
            .sum()
            .head(12)   # next 12 months
        )

        future_months = [
            d.strftime("%b %Y") for d in monthly_forecast.index
        ]

        return jsonify({
            "success": True,
            "kpis": [
                {
                    "month": future_months[i],
                    "value": round(float(monthly_forecast.iloc[i]), 2)
                }
                for i in range(len(monthly_forecast))
            ]
        })

    except Exception as e:
        print("FUTURE FORECAST ERROR:", e)
        return jsonify({
            "success": False,
            "message": "Forecast calculation failed"
        })


@app.route("/api/forecast-chart")
def forecast_chart():
    if "user_id" not in session:
        return jsonify({"success": False}), 401

    df = load_user_csv(session["user_id"])
    df = process_sales_data(df)

    # ---------------- MONTHLY SALES ----------------
    monthly = (
        df.set_index("date")
        .resample("ME")["sales"]
        .sum()
    )

    if len(monthly) < 6:
        return jsonify({
            "success": False,
            "message": "Not enough data for forecasting"
        })

    # ---------------- SARIMA MODEL ----------------
    model = SARIMAX(
        monthly,
        order=(1, 1, 1),
        seasonal_order=(1, 1, 1, 12)
    )

    results = model.fit(disp=False)

    # Forecast next 6 months
    forecast_steps = 6
    forecast = results.get_forecast(steps=forecast_steps)
    forecast_values = forecast.predicted_mean

    # ---------------- LABELS ----------------
    historical_labels = [d.strftime("%b %Y") for d in monthly.index]
    future_labels = [
        (monthly.index[-1] + pd.DateOffset(months=i+1)).strftime("%b %Y")
        for i in range(forecast_steps)
    ]

    return jsonify({
        "success": True,
        "labels": historical_labels + future_labels,
        "historical": [float(v) for v in monthly.values] + [None] * forecast_steps,
        "predicted": [None] * len(monthly.values) + [float(v) for v in forecast_values]
    })


@app.route("/api/inventory")
def inventory():
    if "user_id" not in session:
        return jsonify({"success": False}), 401

    df = load_user_csv(session["user_id"])
    if df is None:
        return jsonify({"success": False})

    df = process_sales_data(df)

    if "stock_left" not in df.columns or "quantity" not in df.columns:
        return jsonify({
            "success": True,
            "forecast": 0,
            "current_stock": 0,
            "action": "No Data"
        })

    # ---------- CURRENT STOCK ----------
    current_stock = int(df["stock_left"].sum())

    # ---------- TOTAL QUANTITY (🔥 MISSING FIX) ----------
    total_quantity = df["quantity"].sum()

    # ---------- FORECAST DEMAND ----------
    monthly_demand = (
        df.set_index("date")
        .resample("ME")["quantity"]
        .sum()
    )
    forecast_demand = int(monthly_demand.tail(3).mean()) if len(monthly_demand) else 0

    # ---------- SAFE DAILY SALES ----------
    if total_quantity <= 0:
        return jsonify({
            "success": True,
            "forecast": forecast_demand,
            "current_stock": current_stock,
            "action": "No Sales Data"
        })

    total_days = max((df["date"].max() - df["date"].min()).days, 1)
    avg_daily_sales = total_quantity / total_days
    days_left = round(current_stock / avg_daily_sales, 1)

    # ---------- ACTION ----------
    if days_left < 10:
        action = "Urgent Reorder Required"
    elif days_left < 20:
        action = "Reorder Soon"
    else:
        action = "Stock Sufficient"

    return jsonify({
        "success": True,
        "forecast": forecast_demand,
        "current_stock": current_stock,
        "action": action
    })


@app.route("/api/categories")
def get_categories():
    if "user_id" not in session:
        return jsonify({"success": False}), 401

    df = load_user_csv(session["user_id"])
    df = process_sales_data(df)

    categories = sorted(df["category"].dropna().unique().tolist())

    return jsonify({
        "success": True,
        "categories": categories
    })
@app.route("/api/category-summary", methods=["POST"])
def category_summary():
    if "user_id" not in session:
        return jsonify({"success": False}), 401

    data = request.get_json()
    category = data.get("category")

    df = load_user_csv(session["user_id"])
    df = process_sales_data(df)

    cat_df = df[df["category"] == category]

    if cat_df.empty:
        return jsonify({"success": False})

    total_sales = float(cat_df["sales"].sum())
    total_profit = float(cat_df["profit"].sum())

    best_item = (
        cat_df.groupby("item_name")["quantity"]
        .sum()
        .idxmax()
    )

    worst_item = (
        cat_df.groupby("item_name")["quantity"]
        .sum()
        .idxmin()
    )

    return jsonify({
        "success": True,
        "total_sales": round(total_sales, 2),
        "total_profit": round(total_profit, 2),
        "best_item": str(best_item),
        "worst_item": str(worst_item)
    })
@app.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Invalid request"}), 400

    email = data.get("email")
    new_password = data.get("password")

    if not email or not new_password:
        return jsonify({"success": False, "message": "Missing fields"}), 400

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()

       
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        user = cur.fetchone()

        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        hashed_password = generate_password_hash(new_password)

        cur.execute(
            "UPDATE users SET password = %s WHERE email = %s",
            (hashed_password, email)
        )

        conn.commit()   
        return jsonify({"success": True})

    except Exception as e:
        print("RESET ERROR:", e)
        return jsonify({"success": False, "message": "Reset failed"}), 500

    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
