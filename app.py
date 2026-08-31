"""
app.py
Sales & Business Analytics Dashboard
-------------------------------------
A Flask backend that:
  - Accepts CSV uploads and loads them into a SQL database
  - Exposes a JSON API that runs SQL queries for KPIs, charts, and filters
  - Lets the user export a filtered report as CSV

No login -- this is a single-user local tool.

Run:
    pip install -r requirements.txt
    python database.py      # create tables once
    python app.py             # start the server on http://127.0.0.1:5000
"""

import os
import io
import csv

import pandas as pd
from flask import Flask, render_template, request, jsonify, Response

from database import get_connection, init_db

app = Flask(__name__)

REQUIRED_COLUMNS = {"order_date", "region", "category", "product", "quantity", "unit_price"}


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


# ---------------------------------------------------------------------------
# CSV upload -> SQL
# ---------------------------------------------------------------------------

@app.route("/api/upload", methods=["POST"])
def upload_csv():
    file = request.files.get("file")
    if not file or file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not file.filename.lower().endswith(".csv"):
        return jsonify({"error": "Please upload a .csv file."}), 400

    try:
        df = pd.read_csv(file)
    except Exception as exc:
        return jsonify({"error": f"Could not read CSV: {exc}"}), 400

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        return jsonify({
            "error": f"CSV is missing required columns: {', '.join(sorted(missing))}"
        }), 400

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0)
    df["revenue"] = df["quantity"] * df["unit_price"]
    df = df.dropna(subset=["order_date"])

    conn = get_connection()
    cur = conn.cursor()

    rows = [
        (
            str(row["order_date"]), row.get("region", ""), row.get("category", ""),
            row.get("product", ""), int(row["quantity"]), float(row["unit_price"]),
            float(row["revenue"]),
        )
        for _, row in df.iterrows()
    ]

    cur.executemany(
        """INSERT INTO sales (order_date, region, category, product, quantity, unit_price, revenue)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    cur.execute(
        "INSERT INTO uploads (filename, row_count) VALUES (?, ?)",
        (file.filename, len(rows)),
    )
    conn.commit()
    conn.close()

    return jsonify({"message": f"Imported {len(rows)} rows from {file.filename}."})


@app.route("/api/load-sample", methods=["POST"])
def load_sample():
    sample_path = os.path.join(os.path.dirname(__file__), "sample_data", "sample_sales.csv")
    if not os.path.exists(sample_path):
        return jsonify({"error": "Sample data file not found."}), 404

    df = pd.read_csv(sample_path)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(0)
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce").fillna(0)
    df["revenue"] = df["quantity"] * df["unit_price"]

    conn = get_connection()
    cur = conn.cursor()
    rows = [
        (
            str(row["order_date"]), row.get("region", ""), row.get("category", ""),
            row.get("product", ""), int(row["quantity"]), float(row["unit_price"]),
            float(row["revenue"]),
        )
        for _, row in df.iterrows()
    ]
    cur.executemany(
        """INSERT INTO sales (order_date, region, category, product, quantity, unit_price, revenue)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )
    cur.execute("INSERT INTO uploads (filename, row_count) VALUES (?, ?)", ("sample_sales.csv", len(rows)))
    conn.commit()
    conn.close()

    return jsonify({"message": f"Loaded {len(rows)} sample rows."})


@app.route("/api/reset", methods=["POST"])
def reset_data():
    """Clears all sales data -- lets the user start over from an empty state."""
    conn = get_connection()
    conn.execute("DELETE FROM sales")
    conn.execute("DELETE FROM uploads")
    conn.commit()
    conn.close()
    return jsonify({"message": "All data cleared."})


# ---------------------------------------------------------------------------
# Filter helper (shared by KPIs, charts, export)
# ---------------------------------------------------------------------------

def build_filters(args):
    clauses = ["1=1"]
    params = []

    if args.get("start_date"):
        clauses.append("order_date >= ?")
        params.append(args["start_date"])
    if args.get("end_date"):
        clauses.append("order_date <= ?")
        params.append(args["end_date"])
    if args.get("region") and args["region"] != "all":
        clauses.append("region = ?")
        params.append(args["region"])
    if args.get("category") and args["category"] != "all":
        clauses.append("category = ?")
        params.append(args["category"])

    return " AND ".join(clauses), params


# ---------------------------------------------------------------------------
# Analytics API
# ---------------------------------------------------------------------------

@app.route("/api/filters")
def api_filter_options():
    conn = get_connection()
    regions = [r["region"] for r in conn.execute(
        "SELECT DISTINCT region FROM sales WHERE region != '' ORDER BY region"
    ).fetchall()]
    categories = [c["category"] for c in conn.execute(
        "SELECT DISTINCT category FROM sales WHERE category != '' ORDER BY category"
    ).fetchall()]
    has_data = conn.execute("SELECT COUNT(*) AS c FROM sales").fetchone()["c"] > 0
    conn.close()
    return jsonify({"regions": regions, "categories": categories, "has_data": has_data})


@app.route("/api/kpis")
def api_kpis():
    where_clause, params = build_filters(request.args)
    conn = get_connection()
    row = conn.execute(f"""
        SELECT
            COALESCE(SUM(revenue), 0) AS total_revenue,
            COALESCE(SUM(quantity), 0) AS total_units,
            COUNT(*) AS total_orders,
            COALESCE(AVG(revenue), 0) AS avg_order_value
        FROM sales WHERE {where_clause}
    """, params).fetchone()
    conn.close()
    return jsonify(dict(row))


@app.route("/api/revenue-trend")
def api_revenue_trend():
    where_clause, params = build_filters(request.args)
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT order_date, SUM(revenue) AS revenue
        FROM sales WHERE {where_clause}
        GROUP BY order_date ORDER BY order_date
    """, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/top-products")
def api_top_products():
    where_clause, params = build_filters(request.args)
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT product, SUM(revenue) AS revenue
        FROM sales WHERE {where_clause}
        GROUP BY product ORDER BY revenue DESC LIMIT 8
    """, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/region-breakdown")
def api_region_breakdown():
    where_clause, params = build_filters(request.args)
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT region, SUM(revenue) AS revenue
        FROM sales WHERE {where_clause}
        GROUP BY region ORDER BY revenue DESC
    """, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/table")
def api_table():
    where_clause, params = build_filters(request.args)
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT order_date, region, category, product, quantity, unit_price, revenue
        FROM sales WHERE {where_clause}
        ORDER BY order_date DESC LIMIT 200
    """, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/export")
def api_export():
    where_clause, params = build_filters(request.args)
    conn = get_connection()
    rows = conn.execute(f"""
        SELECT order_date, region, category, product, quantity, unit_price, revenue
        FROM sales WHERE {where_clause}
        ORDER BY order_date DESC
    """, params).fetchall()
    conn.close()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["order_date", "region", "category", "product", "quantity", "unit_price", "revenue"])
    for r in rows:
        writer.writerow([r["order_date"], r["region"], r["category"], r["product"],
                          r["quantity"], r["unit_price"], r["revenue"]])

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=sales_report.csv"},
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
