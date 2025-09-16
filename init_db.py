# init_db.py
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "employees.db")

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # إنشاء جدول web_users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS web_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        department_id INTEGER NULL
    )
    """)
    
    # إنشاء جدول departments
    cur.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    )
    """)
    
    # إنشاء جدول employees مع العمود department_id
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        national_id TEXT UNIQUE,
        serial_number TEXT,
        name TEXT NOT NULL,
        job_grade TEXT,
        bonus INTEGER,
        grade_date TEXT,
        hiring_date TEXT,
        vacation_balance INTEGER,
        department_id INTEGER,
        work_days INTEGER,
        FOREIGN KEY (department_id) REFERENCES departments (id)
    )
    """)
    
    # إنشاء جدول vacations
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vacations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT NOT NULL,
        dept_approved_by INTEGER NULL,
        dept_approved_at TEXT NULL,
        manager_approved_by INTEGER NULL,
        manager_approved_at TEXT NULL,
        FOREIGN KEY (employee_id) REFERENCES employees (id),
        FOREIGN KEY (dept_approved_by) REFERENCES web_users (id),
        FOREIGN KEY (manager_approved_by) REFERENCES web_users (id)
    )
    """)
    
    # إضافة بعض البيانات الأساسية
    cur.execute("INSERT OR IGNORE INTO departments (name) VALUES ('الإدارة')")
    cur.execute("INSERT OR IGNORE INTO departments (name) VALUES ('المالية')")
    cur.execute("INSERT OR IGNORE INTO departments (name) VALUES ('الموارد البشرية')")
    cur.execute("INSERT OR IGNORE INTO departments (name) VALUES ('التقنية')")
    
    conn.commit()
    conn.close()
    print("تم تهيئة قاعدة البيانات بنجاح!")

if __name__ == "__main__":
    init_database()