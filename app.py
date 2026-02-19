import psycopg2
from psycopg2.extras  import RealDictCursor
import io
from flask import send_file
from flask import Flask, request, jsonify, redirect, url_for, render_template, session
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail as SendGridMail

import os
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import pandas as pd
from flask_mail import Mail, Message
import random
import datetime




app = Flask(__name__, static_folder="static")  
mail = Mail(app)

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
        return None

    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return None

    if "date" not in df.columns:
        return None

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def process_sales_data(df):
    
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

   
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    if "cost_price" not in df.columns:
        df["cost_price"] = df["selling_price"] * 0.7  # fallback

    df["profit"] = (df["selling_price"] - df["cost_price"]) * df["quantity"]

    df["sales"] = df["selling_price"] * df["quantity"]
   
    return df



def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is NOT set")
    return psycopg2.connect(db_url)

    










def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS



@app.route("/")
def index():
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/faqs")
def faqs():
    return render_template("faqs.html")




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
@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    email = data.get("email")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    conn.close()

    if not user:
        return jsonify({"success": False, "message": "Email not registered"})

    otp = str(random.randint(100000, 999999))

    session["reset_email"] = email
    session["reset_otp"] = otp
    session["otp_expiry"] = (
        datetime.datetime.now() + datetime.timedelta(minutes=5)
    ).isoformat()

   
    sender_email = os.environ.get("SENDGRID_SENDER_EMAIL")
    
    message = SendGridMail(
        from_email=sender_email,
        to_emails=email,
        subject="Retail Sense - Password Reset OTP",
        plain_text_content=f"Your OTP is {otp}. Valid for 5 minutes."
    )

    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
    except Exception as e:
        print("SENDGRID ERROR:", e)
        return jsonify({"success": False, "message": "Failed to send email."}), 500

    return jsonify({"success": True})
    

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if "user_id" not in session:
        return jsonify({"success": False, "redirect": url_for("index")}), 401

    if request.method == "GET":
        return render_template("upload.html")

   
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







@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))




    
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("index"))

    
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT csv_uploaded, csv_path FROM users WHERE id = %s",
        (session["user_id"],)
    )
    csv_uploaded, csv_path = cur.fetchone()
    conn.close()

    
    if not csv_uploaded:
        return redirect(url_for("upload"))

    if not csv_path or not os.path.exists(csv_path):
        return render_template(
            "upload.html",
            error="CSV file missing. Please re-upload."
        )

    

    df = pd.read_csv(csv_path)
    df = process_sales_data(df)

    
    total_sales = round(df["sales"].sum(), 2)
    net_profit = round(df["profit"].sum(), 2)
    avg_profit = round(df["profit"].mean(), 2)

    top_item = df.groupby("item_name")["quantity"].sum().idxmax()
    
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

    top_5_items = [
    {
        "name": row["item_name"],
        "units_sold": int(row["units_sold"]),
        "revenue": round(row["revenue"], 2)
    }
    for _, row in top_5_df.iterrows()
    ]

    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT email FROM users WHERE id = %s", (session["user_id"],))
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
    bottom_3_categories=bottom_3_categories
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
    df = load_user_csv(session["user_id"])
    if df is None:
        return jsonify({
            "success": False,
            "message": "CSV not found. Please upload again."
        }), 400

    df = process_sales_data(df)

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
    if len(filtered_df) > 50000:
        return jsonify({
            "success": False,
            "message": "Too much data to export. Please narrow date range."
        }), 400

    filtered_df.to_excel(output, index=False)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name="datewise_report.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# @app.errorhandler(Exception)
# def handle_exception(e):
#     print("UNHANDLED ERROR:", e)
#     return jsonify({"error": str(e)}), 500


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

    
    current_stock = int(df["stock_left"].sum())

   
    total_quantity = df["quantity"].sum()

    
    monthly_demand = (
        df.set_index("date")
        .resample("ME")["quantity"]
        .sum()
    )
    forecast_demand = int(monthly_demand.tail(3).mean()) if len(monthly_demand) else 0

    
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
@app.route("/api/change-password", methods=["POST"])
def change_password():
    
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized access"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "message": "Invalid request"}), 400

    current_password = data.get("current_password")
    new_password = data.get("new_password")

    
    if not current_password or not new_password:
        return jsonify({"success": False, "message": "Both password fields are required"}), 400
    if len(new_password) < 8:
        return jsonify({"success": False, "message": "New password must be at least 8 characters long"}), 400

    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()

       
        cur.execute("SELECT password FROM users WHERE id = %s", (session["user_id"],))
        result = cur.fetchone()

        if not result:
            return jsonify({"success": False, "message": "User not found"}), 404

        stored_hash = result[0]

        if not check_password_hash(stored_hash, current_password):
            return jsonify({"success": False, "message": "Current password is incorrect"}), 401

        
        new_hash = generate_password_hash(new_password)
        
        cur.execute(
            "UPDATE users SET password = %s WHERE id = %s",
            (new_hash, session["user_id"])
        )
        conn.commit()

        return jsonify({"success": True, "message": "Password updated successfully"})

    except Exception as e:
        print("CHANGE PASSWORD ERROR:", e)
        return jsonify({"success": False, "message": "Server error"}), 500

    finally:
        if conn:
            conn.close()
@app.route("/api/product-intelligence")
def product_intelligence():
    if "user_id" not in session:
        return jsonify({"success": False}), 401

    df = load_user_csv(session["user_id"])
    df = process_sales_data(df)

    
    product_df = (
        df.groupby("item_name")
        .agg(
            revenue=("sales", "sum"),
            quantity=("quantity", "sum"),
            profit=("profit", "sum")
        )
        .reset_index()
    )

    
    product_df = product_df.sort_values("revenue", ascending=False)
    total_revenue = product_df["revenue"].sum()
    product_df["cum_pct"] = product_df["revenue"].cumsum() / total_revenue * 100

    def abc_class(p):
        if p <= 80:
            return "A"
        elif p <= 95:
            return "B"
        return "C"

    product_df["abc_class"] = product_df["cum_pct"].apply(abc_class)

    
    avg_profit = product_df["profit"].mean()
    avg_qty = product_df["quantity"].mean()

    def quadrant(row):
        if row["profit"] >= avg_profit and row["quantity"] >= avg_qty:
            return "Star"
        elif row["profit"] < avg_profit and row["quantity"] >= avg_qty:
            return "Cash Cow"
        elif row["profit"] >= avg_profit and row["quantity"] < avg_qty:
            return "Opportunity"
        return "Dog"

    product_df["quadrant"] = product_df.apply(quadrant, axis=1)

    return jsonify({
        "success": True,
        "products": product_df.to_dict(orient="records")
    })
@app.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()

    email = data.get("email")
    otp = data.get("otp")
    new_password = data.get("new_password")

    if email != session.get("reset_email"):
        return jsonify({"success": False, "message": "Invalid request"})

    if otp != session.get("reset_otp"):
        return jsonify({"success": False, "message": "Invalid OTP"})

    expiry = session.get("otp_expiry")
    if not expiry:
        return jsonify({"success": False, "message": "OTP expired"})

    if datetime.datetime.now() > datetime.datetime.fromisoformat(expiry):
        return jsonify({"success": False, "message": "OTP expired"})

    if len(new_password) < 8:
        return jsonify({"success": False, "message": "Password must be at least 8 characters"})

    new_hash = generate_password_hash(new_password)

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET password = %s WHERE email = %s",
        (new_hash, email)
    )
    conn.commit()
    conn.close()

    session.pop("reset_email", None)
    session.pop("reset_otp", None)
    session.pop("otp_expiry", None)

    return jsonify({"success": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
