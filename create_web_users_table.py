# create_web_users_table.py
import sqlite3

DB_PATH = "employees.db"  # تأكد من أن هذا هو نفس مسار قاعدة البيانات

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS web_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    department_id INTEGER NULL
)
""")
conn.commit()
conn.close()