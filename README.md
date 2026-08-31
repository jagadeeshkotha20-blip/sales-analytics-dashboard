# Ledgerline — Sales & Business Analytics Dashboard

A full-stack analytics web app that turns a raw sales CSV into a live,
interactive dashboard: revenue trends, regional breakdowns, top products,
and a filterable order table — all backed by real SQL queries.

No login, no account setup. Open it and drop in a CSV.

## Features

- **Drag-and-drop CSV upload** — parsed with pandas, loaded straight into SQL
- **Live KPIs** — total revenue, units sold, order count, average order value
- **Charts** (Chart.js) — revenue trend, revenue by region, top products
- **Filtering** — by date range, region, category — every filter re-runs real SQL queries
- **CSV export** — download the currently filtered data
- **Sample data** — one click to explore the dashboard without your own file
- **Self-hosted fonts and charting library** — nothing loads from a CDN, so it works even with strict browser tracking-prevention settings, and fully offline after first load

## Tech Stack

| Layer      | Technology                          |
|------------|--------------------------------------|
| Frontend   | HTML, CSS, vanilla JavaScript, Chart.js |
| Backend    | Python (Flask), pandas               |
| Database   | SQLite (swap-in ready for MySQL/PostgreSQL) |
| Fonts      | Fraunces (display) + Inter (UI), self-hosted |

## Setup

```bash
pip install -r requirements.txt
python database.py      # create tables once
python app.py             # start the server
```

Visit `http://127.0.0.1:5000`. Drop in a CSV, or click **"Try it with sample data."**

## CSV Format Expected

```
order_date, region, category, product, quantity, unit_price
```

`revenue` is calculated automatically as `quantity × unit_price`. Column
names are case-insensitive; spaces become underscores.

## Database Schema

```sql
CREATE TABLE sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_date TEXT NOT NULL,
    region TEXT,
    category TEXT,
    product TEXT,
    quantity INTEGER,
    unit_price REAL,
    revenue REAL
);

CREATE TABLE uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    row_count INTEGER,
    uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## Resume Bullet (example)

> Built a full-stack sales analytics dashboard (Flask, SQL, JS/Chart.js) that
> ingests CSV data via drag-and-drop, stores it relationally, and serves live
> KPI and chart queries through a REST API with date/region/category
> filtering and CSV export.
