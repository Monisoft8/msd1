# app.py
# نظام إدارة الموظفين - نسخة منقحة كاملة
# تعديلات رئيسية:
# - توحيد إدارة الحسابات في جدول web_users فقط (إلغاء تخزين كلمات المرور في جدول departments)
# - إنشاء حساب رئيس القسم في web_users عند تهيئة الأقسام الافتراضية أو عند إضافة قسم جديد
# - تبسيط وتثبيت دوال تسجيل الدخول والتحقق
# - الحفاظ على جميع الراوتات والوظائف الموجودة في ملفك الأصلي (غيّرت المنطق فقط حيث كان خاطئاً)

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

# توجيه stdout إلى stderr ليتوافق مع بيئات معينة
sys.stdout = sys.stderr

# إعداد logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# مسار قاعدة البيانات
DB_PATH = os.path.join(os.path.dirname(__file__), "employees.db")

app = Flask(__name__)
app.secret_key = os.environ.get("EMP_SYS_SECRET", "change_this_secret_12345")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ------------------------
# نماذج البيانات (User)
# ------------------------
class WebUser(UserMixin):
    def __init__(self, id, username, role, dept_id=None, dept_name=None):
        # id كـ str لتوافق Flask-Login
        self.id = str(id)
        self.username = username
        self.role = role
        self.dept_id = dept_id
        self.dept_name = dept_name


# ------------------------
# دوال قاعدة البيانات
# ------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """
    تهيئة الجداول الأساسية في قاعدة البيانات.
    ملاحظة: لا يتم حذف قاعدة البيانات هنا تلقائياً.
    """
    conn = get_conn()
    cur = conn.cursor()

    # جدول web_users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS web_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        department_id INTEGER NULL,
        FOREIGN KEY (department_id) REFERENCES departments(id)
    )
    """)

    # جدول departments (بدون head_password)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        head_username TEXT NULL
    )
    """)

    # جدول employees
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        serial_number TEXT,
        name TEXT NOT NULL,
        national_id TEXT UNIQUE,
        hiring_date TEXT,
        job_grade TEXT,
        bonus INTEGER DEFAULT 0,
        grade_date TEXT,
        vacation_balance INTEGER DEFAULT 30,
        emergency_vacation_balance INTEGER DEFAULT 3,
        department_id INTEGER,
        work_days TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (department_id) REFERENCES departments (id)
    )
    """)

    # جدول vacations
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vacations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        relation TEXT NULL,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        duration INTEGER NOT NULL,
        notes TEXT,
        status TEXT DEFAULT 'pending',
        dept_approval TEXT DEFAULT 'pending',
        manager_approval TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        dept_approved_at TEXT NULL,
        manager_approved_at TEXT NULL,
        rejection_reason TEXT NULL,
        FOREIGN KEY (employee_id) REFERENCES employees (id)
    )
    """)

    # جدول absences
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

    # جدول audit_log
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
    cur.execute("SELECT id FROM web_users WHERE role = 'manager'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO web_users (username, password_hash, role) VALUES (?, ?, 'manager')",
            ("admin", bcrypt.hash("admin123"))
        )

    conn.commit()
    conn.close()
    logger.info("تم تهيئة قاعدة البيانات بنجاح")


def find_user_by_username(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT wu.id, wu.username, wu.password_hash, wu.role, wu.department_id, d.name as dept_name
        FROM web_users wu 
        LEFT JOIN departments d ON wu.department_id = d.id 
        WHERE wu.username = ?
    """, (username,))
    row = cur.fetchone()
    conn.close()
    return row


@login_manager.user_loader
def load_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT wu.id, wu.username, wu.role, wu.department_id, d.name as dept_name
        FROM web_users wu 
        LEFT JOIN departments d ON wu.department_id = d.id 
        WHERE wu.id = ?
    """, (user_id,))
    r = cur.fetchone()
    conn.close()
    if not r:
        return None
    return WebUser(r["id"], r["username"], r["role"], r["department_id"], r["dept_name"])


# ------------------------
# Routes
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


# ---------- Dashboard المدير ----------
@app.route("/manager")
@login_required
def manager_dashboard():
    if current_user.role != "manager":
        return "مرفوض", 403

    conn = get_conn()
    cur = conn.cursor()

    # إحصائيات سريعة
    cur.execute("SELECT COUNT(*) FROM employees")
    total_employees = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM vacations WHERE status='pending'")
    pending_vacations = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM absences WHERE date = date('now')")
    today_absences = cur.fetchone()[0]

    # طلبات الإجازات المعلقة
    cur.execute("""
        SELECT v.*, e.name AS employee_name, d.name as dept_name
        FROM vacations v 
        JOIN employees e ON v.employee_id = e.id 
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE v.status='pending'
        ORDER BY v.created_at DESC
    """)
    vacation_requests = cur.fetchall()

    conn.close()

    return render_template("manager_dashboard.html",
                           total_employees=total_employees,
                           pending_vacations=pending_vacations,
                           today_absences=today_absences,
                           vacation_requests=vacation_requests)


# ---------- Dashboard رئيس القسم ----------
@app.route("/dept")
@login_required
def dept_dashboard():
    if current_user.role != "dept_head":
        return "مرفوض", 403

    conn = get_conn()
    cur = conn.cursor()

    # طلبات إجازات القسم
    cur.execute("""
        SELECT v.*, e.name AS employee_name
        FROM vacations v 
        JOIN employees e ON v.employee_id = e.id 
        WHERE e.department_id = ? AND v.dept_approval='pending'
        ORDER BY v.created_at DESC
    """, (current_user.dept_id,))
    vacation_requests = cur.fetchall()

    # إحصائيات القسم
    cur.execute("SELECT COUNT(*) FROM employees WHERE department_id = ?", (current_user.dept_id,))
    dept_employees = cur.fetchone()[0]

    # غياب اليوم للقسم
    cur.execute("""
        SELECT COUNT(*) FROM absences a
        JOIN employees e ON a.employee_id = e.id
        WHERE e.department_id = ? AND a.date = date('now')
    """, (current_user.dept_id,))
    today_dept_absences = cur.fetchone()[0]

    conn.close()

    return render_template("dept_dashboard.html",
                           dept_employees=dept_employees,
                           today_absences=today_dept_absences,
                           vacation_requests=vacation_requests)


# ---------- Employees إدارة الموظفين ----------
@app.route("/employees")
@login_required
def employees_list():
    if current_user.role != "manager":
        return "مرفوض", 403

    conn = get_conn()
    cur = conn.cursor()

    # جلب جميع الموظفين
    cur.execute("""
        SELECT e.*, d.name as dept_name 
        FROM employees e 
        LEFT JOIN departments d ON e.department_id = d.id
        ORDER BY e.name
    """)
    employees = cur.fetchall()

    # جلب الأقسام
    cur.execute("SELECT id, name FROM departments ORDER BY name")
    departments = cur.fetchall()

    conn.close()

    return render_template("employees.html", employees=employees, departments=departments)


@app.route("/employees/add", methods=["POST"])
@login_required
def add_employee():
    if current_user.role != "manager":
        return jsonify({"error": "غير مصرح"}), 403

    try:
        data = request.get_json() or request.form
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO employees (serial_number, name, national_id, department_id, job_grade, 
                                 hiring_date, grade_date, bonus, vacation_balance, work_days)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('serial_number'),
            data.get('name'),
            data.get('national_id'),
            data.get('department_id'),
            data.get('job_grade'),
            data.get('hiring_date'),
            data.get('grade_date'),
            int(data.get('bonus', 0)),
            int(data.get('vacation_balance', 30)),
            data.get('work_days', '')
        ))

        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "تم إضافة الموظف بنجاح"})

    except Exception as e:
        logger.exception("خطأ في إضافة موظف")
        return jsonify({"error": str(e)}), 500


# ---------- Vacations إدارة الإجازات ----------
@app.route("/vacations")
@login_required
def vacations_list():
    conn = get_conn()
    cur = conn.cursor()

    if current_user.role == "manager":
        cur.execute("""
            SELECT v.*, e.name AS employee_name, d.name as department
            FROM vacations v 
            JOIN employees e ON v.employee_id = e.id 
            LEFT JOIN departments d ON e.department_id = d.id
            ORDER BY v.created_at DESC
        """)
    else:
        # رئيس القسم يرى إجازات قسمه
        cur.execute("""
            SELECT v.*, e.name AS employee_name
            FROM vacations v 
            JOIN employees e ON v.employee_id = e.id 
            WHERE e.department_id = ?
            ORDER BY v.created_at DESC
        """, (current_user.dept_id,))

    vacations = cur.fetchall()
    conn.close()

    return render_template("vacations.html", vacations=vacations)


@app.route("/vacations/add", methods=["POST"])
@login_required
def add_vacation():
    try:
        data = request.get_json() or request.form
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO vacations (employee_id, type, start_date, end_date, duration, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get('employee_id'),
            data.get('type'),
            data.get('start_date'),
            data.get('end_date'),
            data.get('duration'),
            data.get('notes', '')
        ))

        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "تم تقديم طلب الإجازة بنجاح"})

    except Exception as e:
        logger.exception("خطأ في إضافة إجازة")
        return jsonify({"error": str(e)}), 500


# ---------- Approvals الموافقات ----------
@app.route("/approve/vacation/<int:vacation_id>", methods=["POST"])
@login_required
def approve_vacation(vacation_id):
    try:
        conn = get_conn()
        cur = conn.cursor()

        if current_user.role == "dept_head":
            cur.execute("""
                UPDATE vacations SET dept_approval='approved', dept_approved_at=datetime('now')
                WHERE id=? AND dept_approval='pending'
            """, (vacation_id,))
        elif current_user.role == "manager":
            cur.execute("""
                UPDATE vacations SET status='approved', manager_approved_at=datetime('now')
                WHERE id=? AND status='pending'
            """, (vacation_id,))
        else:
            conn.close()
            return jsonify({"error": "غير مصرح"}), 403

        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "تمت الموافقة على الإجازة"})

    except Exception as e:
        logger.exception("خطأ في الموافقة على إجازة")
        return jsonify({"error": str(e)}), 500


@app.route("/reject/vacation/<int:vacation_id>", methods=["POST"])
@login_required
def reject_vacation(vacation_id):
    try:
        data = request.get_json() or request.form
        reason = data.get('reason', '')

        conn = get_conn()
        cur = conn.cursor()

        if current_user.role == "dept_head":
            cur.execute("""
                UPDATE vacations SET dept_approval='rejected', dept_approved_at=datetime('now'), rejection_reason=?
                WHERE id=?
            """, (reason, vacation_id))
        elif current_user.role == "manager":
            cur.execute("""
                UPDATE vacations SET status='rejected', manager_approved_at=datetime('now'), rejection_reason=?
                WHERE id=?
            """, (reason, vacation_id))
        else:
            conn.close()
            return jsonify({"error": "غير مصرح"}), 403

        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "تم رفض الإجازة"})

    except Exception as e:
        logger.exception("خطأ في رفض إجازة")
        return jsonify({"error": str(e)}), 500


# ---------- Absences إدارة الغياب ----------
@app.route("/absences")
@login_required
def absences_list():
    conn = get_conn()
    cur = conn.cursor()

    # جلب جميع سجلات الغياب
    cur.execute("""
        SELECT a.*, e.name AS employee_name, d.name as department
        FROM absences a 
        JOIN employees e ON a.employee_id = e.id 
        LEFT JOIN departments d ON e.department_id = d.id
        ORDER BY a.date DESC
    """)
    absences_list_rows = cur.fetchall()

    # جلب جميع الموظفين للفلتر
    if current_user.role == "manager":
        cur.execute("SELECT id, name FROM employees ORDER BY name")
    else:
        cur.execute("SELECT id, name FROM employees WHERE department_id = ? ORDER BY name", (current_user.dept_id,))
    employees = cur.fetchall()

    # إحصائيات
    cur.execute("SELECT COUNT(*) FROM absences")
    total_absences = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM absences WHERE date = date('now')")
    today_absences = cur.fetchone()[0]

    # إنشاء قائمة الأشهر للفلتر
    months = []
    current_year = date.today().year
    for year in range(current_year - 1, current_year + 1):
        for month in range(1, 13):
            months.append({
                'value': f"{year}-{month:02d}",
                'name': f"{year}-{month:02d}"
            })

    conn.close()

    return render_template("absences.html",
                           absences=absences_list_rows,
                           employees=employees,
                           total_absences=total_absences,
                           today_absences=today_absences,
                           months=months,
                           today=date.today().isoformat())


@app.route("/absences/add", methods=["POST"])
@login_required
def add_absence():
    try:
        data = request.get_json() or request.form
        conn = get_conn()
        cur = conn.cursor()

        # التحقق من عدم تكرار الغياب لنفس الموظف في نفس التاريخ
        cur.execute("""
            SELECT id FROM absences 
            WHERE employee_id = ? AND date = ?
        """, (data.get('employee_id'), data.get('date')))

        if cur.fetchone():
            conn.close()
            return jsonify({"error": "تم تسجيل غياب لهذا الموظف في هذا التاريخ مسبقاً"}), 400

        cur.execute("""
            INSERT INTO absences (employee_id, date, type, duration, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get('employee_id'),
            data.get('date'),
            data.get('type'),
            data.get('duration', 1),
            data.get('notes', '')
        ))

        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "تم تسجيل الغياب بنجاح"})

    except Exception as e:
        logger.exception("خطأ في تسجيل غياب")
        return jsonify({"error": str(e)}), 500


@app.route("/absences/delete/<int:absence_id>", methods=["DELETE"])
@login_required
def delete_absence(absence_id):
    try:
        conn = get_conn()
        cur = conn.cursor()

        cur.execute("DELETE FROM absences WHERE id = ?", (absence_id,))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "تم حذف سجل الغياب"})

    except Exception as e:
        logger.exception("خطأ في حذف غياب")
        return jsonify({"error": str(e)}), 500


# ---------- Reports / Export التقارير ----------
@app.route("/export/absences")
@login_required
def export_absences():
    try:
        month = request.args.get('month')
        employee_id = request.args.get('employee')
        abs_type = request.args.get('type')

        conn = get_conn()
        cur = conn.cursor()

        query = """
            SELECT e.name, a.date, a.type, a.duration, a.notes, d.name as department
            FROM absences a
            JOIN employees e ON a.employee_id = e.id
            LEFT JOIN departments d ON e.department_id = d.id
            WHERE 1=1
        """
        params = []

        if month:
            query += " AND strftime('%Y-%m', a.date) = ?"
            params.append(month)

        if employee_id:
            query += " AND a.employee_id = ?"
            params.append(employee_id)

        if abs_type:
            query += " AND a.type = ?"
            params.append(abs_type)

        query += " ORDER BY a.date DESC"

        cur.execute(query, params)
        absences = cur.fetchall()

        # تحويل إلى DataFrame
        df = pd.DataFrame(absences, columns=['الموظف', 'التاريخ', 'النوع', 'المدة', 'ملاحظات', 'القسم'])

        # حفظ في ملف Excel
        filename = f"absences_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join('static', 'exports', filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        df.to_excel(filepath, index=False)

        conn.close()
        return send_file(filepath, as_attachment=True)

    except Exception as e:
        logger.exception("خطأ في تصدير تقرير الغياب")
        return jsonify({"error": str(e)}), 500


# ---------- Departments إدارة الأقسام ----------
@app.route("/departments")
@login_required
def departments_list():
    if current_user.role != "manager":
        return "مرفوض", 403

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT d.*, COUNT(e.id) as employee_count,
               (SELECT COUNT(*) FROM vacations v 
                JOIN employees e ON v.employee_id = e.id 
                WHERE e.department_id = d.id AND v.status = 'pending') as pending_vacations
        FROM departments d
        LEFT JOIN employees e ON d.id = e.department_id
        GROUP BY d.id
        ORDER BY d.name
    """)
    departments = cur.fetchall()

    conn.close()

    return render_template("departments.html", departments=departments)


@app.route("/departments/add", methods=["POST"])
@login_required
def add_department():
    if current_user.role != "manager":
        return jsonify({"error": "غير مصرح"}), 403

    try:
        data = request.get_json() or request.form
        conn = get_conn()
        cur = conn.cursor()

        # إضافة القسم (نخزن head_username فقط في جدول departments)
        cur.execute("""
            INSERT INTO departments (name, head_username)
            VALUES (?, ?)
        """, (
            data.get('name'),
            data.get('head_username')
        ))
        dept_id = cur.lastrowid

        # إنشاء مستخدم لرئيس القسم في جدول web_users
        head_username = data.get('head_username')
        head_password = data.get('head_password')
        if head_username and head_password:
            # تأكد من عدم تكرار اسم المستخدم
            cur.execute("SELECT id FROM web_users WHERE username = ?", (head_username,))
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO web_users (username, password_hash, role, department_id)
                    VALUES (?, ?, 'dept_head', ?)
                """, (
                    head_username,
                    bcrypt.hash(head_password),
                    dept_id
                ))

        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "تم إضافة القسم وإنشاء حساب رئيس القسم"})
    except Exception as e:
        logger.exception("خطأ في إضافة قسم")
        return jsonify({"error": str(e)}), 500


@app.route("/department/<int:dept_id>")
@login_required
def department_details(dept_id):
    conn = get_conn()
    cur = conn.cursor()

    # معلومات القسم
    cur.execute("SELECT * FROM departments WHERE id = ?", (dept_id,))
    department = cur.fetchone()

    # موظفو القسم
    cur.execute("""
        SELECT e.* FROM employees e 
        WHERE e.department_id = ? 
        ORDER BY e.name
    """, (dept_id,))
    employees = cur.fetchall()

    # طلبات الإجازة المعلقة
    cur.execute("""
        SELECT v.*, e.name as employee_name
        FROM vacations v 
        JOIN employees e ON v.employee_id = e.id 
        WHERE e.department_id = ? AND v.status = 'pending'
        ORDER BY v.created_at DESC
    """, (dept_id,))
    pending_vacations = cur.fetchall()

    # غياب اليوم
    cur.execute("""
        SELECT a.*, e.name as employee_name
        FROM absences a 
        JOIN employees e ON a.employee_id = e.id 
        WHERE e.department_id = ? AND a.date = date('now')
        ORDER BY a.created_at DESC
    """, (dept_id,))
    today_absences = cur.fetchall()

    conn.close()

    return render_template("department_details.html",
                           department=department,
                           employees=employees,
                           pending_vacations=pending_vacations,
                           today_absences=today_absences)


# ---------- Dept login (احتياطي للتوافق) ----------
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


# ---------- Import employees from Excel استيراد موظفين ----------
@app.route("/import/employees", methods=["POST"])
@login_required
def import_employees():
    if current_user.role != "manager":
        return "مرفوض", 403

    if 'file' not in request.files:
        flash("لم يتم اختيار ملف", "danger")
        return redirect(url_for("employees_list"))

    file = request.files['file']
    if file.filename == '':
        flash("لم يتم اختيار ملف", "danger")
        return redirect(url_for("employees_list"))

    try:
        # قراءة ملف Excel
        df = pd.read_excel(file)
        logger.info(f"تم تحميل ملف Excel بـ {len(df)} صف")
        logger.info(f"الأعمدة: {list(df.columns)}")

        conn = get_conn()
        cur = conn.cursor()

        # تعيين أسماء الأعمدة المتوقعة
        column_mapping = {
            'serial_number': ['الرقم الآلي', 'serial_number', 'رقم'],
            'name': ['الاسم', 'name', 'اسم'],
            'national_id': ['الرقم الوطني', 'national_id', 'رقم وطني'],
            'hiring_date': ['تاريخ التعيين', 'hiring_date', 'تعيين'],
            'job_grade': ['الدرجة', 'job_grade', 'grade'],
            'bonus': ['العلاوة', 'bonus', 'مكافأة'],
            'grade_date': ['تاريخ الدرجة', 'grade_date', 'ترقية'],
            'vacation_balance': ['رصيد الإجازات', 'vacation_balance', 'إجازات'],
            'department': ['القسم', 'department', 'dept'],
            'work_days': ['أيام العمل', 'work_days', 'أيام']
        }

        # البحث عن الأعمدة الفعلية في الملف
        actual_columns = {}
        df_columns = [str(col).strip() for col in df.columns]

        for eng_col, possible_names in column_mapping.items():
            for col_name in df_columns:
                for possible_name in possible_names:
                    if possible_name in col_name:
                        actual_columns[eng_col] = col_name
                        break
                if eng_col in actual_columns:
                    break

        logger.info(f"الأعمدة المطابقة: {actual_columns}")

        success_count = 0
        error_count = 0

        for index, row in df.iterrows():
            try:
                # استخراج البيانات
                data = {}
                for eng_col, actual_col in actual_columns.items():
                    value = row[actual_col] if actual_col in row else ''
                    if pd.isna(value):
                        value = ''
                    data[eng_col] = str(value).strip()

                department_name = data.get('department', '')
                if department_name:
                    cur.execute("SELECT id FROM departments WHERE name = ?", (department_name,))
                    dept_row = cur.fetchone()
                    if dept_row:
                        department_id = dept_row[0]
                    else:
                        # إنشاء قسم جديد إذا لم يكن موجوداً
                        cur.execute("INSERT INTO departments (name) VALUES (?)", (department_name,))
                        department_id = cur.lastrowid
                else:
                    department_id = None

                # معالجة التواريخ
                hiring_date = str(data.get('hiring_date', '')).split(' ')[0] if data.get('hiring_date') else ''
                grade_date = str(data.get('grade_date', '')).split(' ')[0] if data.get('grade_date') else ''

                # معالجة القيم الرقمية
                try:
                    bonus = int(data.get('bonus', 0)) if data.get('bonus') and str(data.get('bonus')).isdigit() else 0
                except:
                    bonus = 0

                try:
                    vacation_balance = int(data.get('vacation_balance', 30)) if data.get('vacation_balance') and str(data.get('vacation_balance')).isdigit() else 30
                except:
                    vacation_balance = 30

                # التحقق من البيانات الأساسية
                if not data.get('name') or not data.get('national_id'):
                    error_count += 1
                    continue

                # إدخال أو تحديث البيانات
                # نستخدم INSERT OR REPLACE على الافتراض أن national_id فريد
                cur.execute("""
                    INSERT OR REPLACE INTO employees 
                    (serial_number, name, national_id, hiring_date, job_grade, bonus, 
                     grade_date, vacation_balance, work_days, department_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data.get('serial_number', ''),
                    data.get('name', ''),
                    data.get('national_id', ''),
                    hiring_date,
                    data.get('job_grade', ''),
                    bonus,
                    grade_date,
                    vacation_balance,
                    data.get('work_days', ''),
                    department_id
                ))

                success_count += 1

            except Exception as e:
                error_count += 1
                logger.exception(f"خطأ في الصف {index}: {str(e)}")

        conn.commit()
        conn.close()

        flash(f"تم استيراد {success_count} موظف بنجاح. عدد الأخطاء: {error_count}", "success")

    except Exception as e:
        flash(f"خطأ في الاستيراد: {str(e)}", "danger")
        logger.exception("خطأ في استيراد ملف الموظفين")

    return redirect(url_for("employees_list"))


# ------------------------
# Initialization
# ------------------------
@app.before_first_request
def initialize():
    # تهيئة الجداول عند أول طلب
    init_database()


# ------------------------
# تشغيل التطبيق
# ------------------------
if __name__ == "__main__":
    # تهيئة قاعدة البيانات إن لم تكن موجودة
    if not os.path.exists(DB_PATH):
        init_database()
    else:
        # التأكد من تحديث البنية عند تشغيل التطبيق (آمن لوجود فهارس أو أعمدة جديدة)
        init_database()
    app.run(host="0.0.0.0", port=5000, debug=True)
