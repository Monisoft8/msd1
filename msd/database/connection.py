# msd/database/connection.py
"""
Database connection and utilities for MSD Employee Management System
"""

import os
import sqlite3
from flask_login import UserMixin
from passlib.hash import bcrypt


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "employees.db")


def get_conn():
    """Get database connection with Row factory"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database tables and default data"""
    conn = get_conn()
    cur = conn.cursor()
    
    # جدول المستخدمين
    cur.execute("""
    CREATE TABLE IF NOT EXISTS web_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        department_id INTEGER NULL,
        FOREIGN KEY (department_id) REFERENCES departments (id)
    )
    """)
    
    # جدول الأقسام
    cur.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        head_username TEXT
    )
    """)
    
    # جدول الموظفين
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        serial_number TEXT,
        name TEXT NOT NULL,
        national_id TEXT UNIQUE,
        department_id INTEGER,
        job_grade TEXT,
        hiring_date TEXT,
        grade_date TEXT,
        bonus INTEGER DEFAULT 0,
        vacation_balance REAL DEFAULT 30.0,
        initial_vacation_balance REAL,
        emergency_vacation_balance REAL DEFAULT 0.0,
        work_pattern TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (department_id) REFERENCES departments (id)
    )
    """)
    
    # جدول الإجازات
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vacations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        duration REAL NOT NULL,
        notes TEXT,
        status TEXT DEFAULT 'pending',
        dept_approval TEXT,
        manager_approval TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        rejection_reason TEXT NULL,
        FOREIGN KEY (employee_id) REFERENCES employees (id)
    )
    """)
    
    # جدول الغياب
    cur.execute("""
    CREATE TABLE IF NOT EXISTS absences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        type TEXT NOT NULL,
        duration INTEGER DEFAULT 1,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (employee_id) REFERENCES employees (id)
    )
    """)
    
    # جدول سجل المراجعة
    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        action TEXT NOT NULL,
        table_name TEXT NOT NULL,
        record_id INTEGER,
        changes TEXT,
        user_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # أقسام افتراضية + إنشاء حسابات رؤساء الأقسام في web_users
    default_departments = [
        # (dept_name, head_password, head_username)
        ("الإدارة", "admin123", "admin"),
        ("المالية", "finance123", "finance_head"),
        ("الموارد البشرية", "hr123", "hr_head"),
        ("التقنية", "tech123", "tech_head")
    ]
    
    for dept_name, head_password, head_username in default_departments:
        # إنشاء القسم إن لم يكن موجودا
        cur.execute("INSERT OR IGNORE INTO departments (name, head_username) VALUES (?, ?)",
                    (dept_name, head_username))
        # احصل على id القسم
        cur.execute("SELECT id FROM departments WHERE name = ?", (dept_name,))
        dept_row = cur.fetchone()
        dept_id = dept_row["id"] if dept_row else None
        
        # إنشاء مستخدم رئيس القسم إن لم يكن موجودا
        cur.execute("SELECT id FROM web_users WHERE username = ?", (head_username,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO web_users (username, password_hash, role, department_id)
                VALUES (?, ?, 'dept_head', ?)
            """, (head_username, bcrypt.hash(head_password), dept_id))
    
    # إنشاء مستخدم مدير افتراضي إذا لم يكن موجوداً
    cur.execute("SELECT id FROM web_users WHERE username = 'admin'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO web_users (username, password_hash, role) VALUES (?, ?, 'manager')",
            ("admin", bcrypt.hash("admin123"))
        )
    
    conn.commit()
    conn.close()


class WebUser(UserMixin):
    """Web user model for Flask-Login"""
    def __init__(self, id, username, role, dept_id=None, dept_name=None):
        # id كـ str لتوافق Flask-Login
        self.id = str(id)
        self.username = username
        self.role = role
        self.dept_id = dept_id
        self.dept_name = dept_name