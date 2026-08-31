"""
database.py
SQL schema for the Sales Analytics Dashboard.
Single-tenant (no login) -- this is a local tool for one person's data,
so there's no users table or per-account isolation. Uses SQLite for
simplicity; the SQL itself ports cleanly to MySQL/PostgreSQL.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "dashboard.db")


def get_connection():
    # timeout=15 makes SQLite wait instead of failing instantly if the file
    # is briefly locked (common on Windows when a folder is synced by
    # OneDrive). WAL mode also reduces lock contention.
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_date TEXT NOT NULL,
            region TEXT,
            category TEXT,
            product TEXT,
            quantity INTEGER,
            unit_price REAL,
            revenue REAL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            row_count INTEGER,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized at", DB_PATH)
