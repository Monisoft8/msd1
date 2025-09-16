"""
Database connection and utilities for MSD Employee Management System
"""

import os
import sqlite3
from contextlib import contextmanager
from flask import current_app

def _ensure_parent_dir(path: str):
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
    except Exception:
        pass

def get_db_path() -> str:
    # DB_PATH مهيّأ في config.py
    return current_app.config.get("DB_PATH", os.path.join(current_app.root_path, "employees.db"))

def _connect() -> sqlite3.Connection:
    db_path = get_db_path()
    _ensure_parent_dir(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@contextmanager
def get_conn():
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()