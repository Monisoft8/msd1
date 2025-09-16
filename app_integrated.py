# app_integrated.py
"""
Integrated MSD Employee Management System
Combines new modular structure with existing functionality while preserving all routes
"""

import os
import sys
import logging
import sqlite3
import json
from datetime import datetime, date
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, send_file, jsonify
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from passlib.hash import bcrypt
import pandas as pd

# Import modular components
from msd.database.connection import get_conn, init_database, WebUser, DB_PATH
from msd.auth import find_user_by_username, load_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# توجيه stdout إلى stderr ليتوافق مع بيئات معينة
sys.stdout = sys.stderr

app = Flask(__name__)
app.secret_key = os.environ.get("EMP_SYS_SECRET", "change_this_secret_12345")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Register user loader
login_manager.user_loader(load_user)

# Register the new modular employees blueprint
from msd.employees.routes import employees_bp
app.register_blueprint(employees_bp)

# ------------------------
# Legacy Routes (preserved from original app.py)
# ------------------------

@app.route("/")
def index():
    return redirect(url_for("login"))

# ---------- Login (موحد لمدير ورؤساء أقسام) ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user_row = find_user_by_username(username)
        if user_row and bcrypt.verify(password, user_row["password_hash"]):
            user = WebUser(user_row["id"], user_row["username"], user_row["role"],
                          user_row["department_id"], user_row["dept_name"])
            login_user(user)
            if user.role == "manager":
                return redirect(url_for("manager_dashboard"))
            else:
                return redirect(url_for("dept_dashboard"))
        flash("اسم المستخدم أو كلمة المرور غير صحيحة", "danger")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ---------- Department Login (for backward compatibility) ----------
@app.route("/dept_login", methods=["GET", "POST"])
def dept_login():
    """
    هذه الواجهة تبقى من أجل التوافق مع النظام القديم.
    تحدد دور المستخدم من web_users ويقبل فقط دور dept_head.
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user_row = find_user_by_username(username)
        if user_row and user_row["role"] == "dept_head" and bcrypt.verify(password, user_row["password_hash"]):
            user = WebUser(user_row["id"], user_row["username"], user_row["role"], user_row["department_id"], user_row["dept_name"])
            login_user(user)
            return redirect(url_for("dept_dashboard"))

        flash("اسم المستخدم أو كلمة المرور غير صحيحة", "danger")

    return render_template("dept_login.html")


# ---------- Manager Dashboard ----------
@app.route("/manager")
@login_required
def manager_dashboard():
    if current_user.role != "manager":
        flash("غير مصرح لك بالوصول لهذه الصفحة", "danger")
        return redirect(url_for("login"))

    conn = get_conn()
    cur = conn.cursor()

    # إحصائيات الموظفين
    cur.execute("SELECT COUNT(*) FROM employees")
    total_employees = cur.fetchone()[0]

    # الإجازات المعلقة
    cur.execute("SELECT COUNT(*) FROM vacations WHERE status = 'pending'")
    pending_vacations = cur.fetchone()[0]

    # الغياب اليوم (افتراضي - قد نحتاج تحديث هذا لاحقاً)
    today = datetime.now().strftime('%Y-%m-%d')
    cur.execute("SELECT COUNT(*) FROM absences WHERE date = ?", (today,))
    today_absences = cur.fetchone()[0]

    # طلبات الإجازات الأخيرة
    cur.execute("""
        SELECT v.*, e.name as employee_name, d.name as dept_name
        FROM vacations v
        JOIN employees e ON v.employee_id = e.id
        LEFT JOIN departments d ON e.department_id = d.id
        ORDER BY v.created_at DESC
        LIMIT 10
    """)
    vacation_requests = cur.fetchall()

    conn.close()

    return render_template("manager_dashboard.html",
                           total_employees=total_employees,
                           pending_vacations=pending_vacations,
                           today_absences=today_absences,
                           vacation_requests=vacation_requests)


# ---------- Department Dashboard ----------
@app.route("/dept")
@login_required
def dept_dashboard():
    if current_user.role not in ["dept_head", "manager"]:
        flash("غير مصرح لك بالوصول لهذه الصفحة", "danger")
        return redirect(url_for("login"))

    conn = get_conn()
    cur = conn.cursor()

    # إحصائيات القسم
    if current_user.role == "manager":
        # المدير يرى جميع الأقسام
        cur.execute("SELECT COUNT(*) FROM employees")
        dept_employees = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM vacations WHERE status = 'pending'")
        pending_vacations = cur.fetchone()[0]
    else:
        # رئيس القسم يرى قسمه فقط
        cur.execute("SELECT COUNT(*) FROM employees WHERE department_id = ?", (current_user.dept_id,))
        dept_employees = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(*) FROM vacations v
            JOIN employees e ON v.employee_id = e.id
            WHERE e.department_id = ? AND v.status = 'pending'
        """, (current_user.dept_id,))
        pending_vacations = cur.fetchone()[0]

    conn.close()

    return render_template("dept_dashboard.html",
                           dept_employees=dept_employees,
                           pending_vacations=pending_vacations)


# ---------- Other Legacy Routes ----------

@app.route("/departments")
@login_required
def departments_list():
    if current_user.role != "manager":
        return "مرفوض", 403

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM departments ORDER BY name")
    departments = cur.fetchall()
    conn.close()

    return render_template("departments.html", departments=departments)


@app.route("/vacations")
@login_required
def vacations_list():
    conn = get_conn()
    cur = conn.cursor()

    if current_user.role == "manager":
        # المدير يرى جميع الإجازات
        cur.execute("""
            SELECT v.*, e.name as employee_name, d.name as dept_name
            FROM vacations v
            JOIN employees e ON v.employee_id = e.id
            LEFT JOIN departments d ON e.department_id = d.id
            ORDER BY v.created_at DESC
        """)
    else:
        # رئيس القسم يرى إجازات قسمه فقط
        cur.execute("""
            SELECT v.*, e.name as employee_name, d.name as dept_name
            FROM vacations v
            JOIN employees e ON v.employee_id = e.id
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE e.department_id = ?
            ORDER BY v.created_at DESC
        """, (current_user.dept_id,))

    vacations = cur.fetchall()
    conn.close()

    return render_template("vacations.html", vacations=vacations)


@app.route("/absences")
@login_required
def absences_list():
    conn = get_conn()
    cur = conn.cursor()

    if current_user.role == "manager":
        # المدير يرى جميع حالات الغياب
        cur.execute("""
            SELECT a.*, e.name as employee_name, d.name as dept_name
            FROM absences a
            JOIN employees e ON a.employee_id = e.id
            LEFT JOIN departments d ON e.department_id = d.id
            ORDER BY a.created_at DESC
        """)
    else:
        # رئيس القسم يرى غياب قسمه فقط
        cur.execute("""
            SELECT a.*, e.name as employee_name, d.name as dept_name
            FROM absences a
            JOIN employees e ON a.employee_id = e.id
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE e.department_id = ?
            ORDER BY a.created_at DESC
        """, (current_user.dept_id,))

    absences = cur.fetchall()
    conn.close()

    return render_template("absences.html", absences=absences)


@app.route("/import_export")
@login_required
def import_export():
    if current_user.role != "manager":
        return "مرفوض", 403
    return render_template("import_export.html")


# Initialize database if needed
if not os.path.exists(DB_PATH):
    with app.app_context():
        init_database()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)