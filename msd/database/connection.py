"""Database connection utilities."""
import sqlite3
from flask import current_app


def get_conn():
    """Get database connection with Row factory."""
    conn = sqlite3.connect(current_app.config["DB_PATH"], check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn