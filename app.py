import psycopg2
from psycopg2.extras  import RealDictCursor
import io
from flask import send_file
from flask import Flask, request, jsonify, redirect, url_for, render_template, session

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

    df = pd.read_csv(result[0])

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
import os
import os
import psycopg2

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


        

# -------------------- UPLOAD PAGE --------------------
# @app.route("/upload")
# def upload_page():
#     if "user_id" not in session:
#         return redirect(url_for("index"))
#     return render_template("upload.html")


# -------------------- CSV UPLOAD --------------------
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

    # ---------------- FUTURE ANALYTICS (NO ML) ----------------
    monthly_sales = (
    df.set_index("date")
    .resample("ME")["sales"]
    .sum()
)

    growth_rate = monthly_sales.pct_change().mean()
    last_value = monthly_sales.iloc[-1]

    monthly_predictions = []
    current = last_value

    for i in range(3):
        current = current * (1 + growth_rate)

        future_month = (
            monthly_sales.index[-1] + pd.DateOffset(months=i+1)
        ).strftime("%b %Y")

        monthly_predictions.append({
            "month": future_month,
            "predicted_sales": round(current, 2),
            "trend_class": "up" if growth_rate >= 0 else "down",
            "trend_icon": "⬆️" if growth_rate >= 0 else "⬇️",
            "trend_percentage": f"{round(growth_rate * 100, 2)}%"
        })

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
        monthly_predictions=monthly_predictions
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

    # 🔥 CONVERT TO PYTHON TYPES
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



if __name__ == "__main__":
    app.run(debug=True)