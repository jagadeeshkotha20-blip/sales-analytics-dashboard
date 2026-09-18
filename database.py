"""
database.py

SQL schema for the Sales Analytics Dashboard.
Uses SQLite for simplicity.

For Vercel:
- The deployed project filesystem is read-only.
- SQLite is copied to /tmp, which is writable.
- Local development continues using dashboard.db.
"""

import os
import shutil
import sqlite3


# Original database bundled with the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_DB_PATH = os.path.join(BASE_DIR, "dashboard.db")


# Vercel provides a writable /tmp directory.
# Locally, continue using dashboard.db.
if os.environ.get("VERCEL") == "1":
    DB_PATH = "/tmp/dashboard.db"

    # Copy the bundled database to the writable /tmp directory
    # the first time the Vercel function starts.
    if not os.path.exists(DB_PATH):
        shutil.copy2(SOURCE_DB_PATH, DB_PATH)
else:
    DB_PATH = SOURCE_DB_PATH


def get_connection():
    """
    Create and return a SQLite database connection.
    """

    conn = sqlite3.connect(DB_PATH, timeout=15)

    conn.row_factory = sqlite3.Row

    # WAL works because the Vercel database is now inside /tmp.
    conn.execute("PRAGMA journal_mode = WAL")

    return conn


def init_db():
    """
    Create required database tables if they don't already exist.
    """

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
