"""Database schema initialization with new comprehensive schema."""
import sqlite3
import logging
from passlib.hash import bcrypt
from msd.database.connection import get_conn

logger = logging.getLogger(__name__)


def init_database():
    """Initialize database with new comprehensive schema (idempotent)."""
    with get_conn() as conn:
        cur = conn.cursor()
    
    # Enable foreign keys
    cur.execute("PRAGMA foreign_keys = ON")
    
    # Create web_users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS web_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('manager','dept_head','employee')),
        department_id INTEGER NULL,
        employee_id INTEGER NULL,
        telegram_chat_id INTEGER UNIQUE NULL,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (department_id) REFERENCES departments(id),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """)
    
    # Create departments table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        head_user_id INTEGER NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (head_user_id) REFERENCES web_users(id)
    )
    """)
    
    # Create employees table with new schema
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        serial_number TEXT UNIQUE,
        name TEXT NOT NULL,
        national_id TEXT UNIQUE,
        department_id INTEGER,
        job_grade TEXT,
        hiring_date TEXT,
        grade_date TEXT,
        bonus INTEGER DEFAULT 0,
        vacation_balance REAL DEFAULT 30,
        emergency_vacation_balance INTEGER DEFAULT 12,
        initial_vacation_balance REAL NULL,
        work_pattern TEXT,
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (department_id) REFERENCES departments(id)
    )
    """)
    
    # Create employee_work_days table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS employee_work_days (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL CHECK(day_of_week >= 0 AND day_of_week <= 6),
        period TEXT NOT NULL CHECK(period IN ('M','E','F')),
        UNIQUE(employee_id, day_of_week),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """)
    
    # Create vacation_types table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vacation_types (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name_ar TEXT NOT NULL,
        deduct_main_balance INTEGER DEFAULT 0,
        uses_emergency_balance INTEGER DEFAULT 0,
        fixed_duration INTEGER NULL,
        max_days_per_request INTEGER NULL,
        yearly_quota INTEGER NULL,
        lifetime_quota INTEGER NULL,
        requires_docs INTEGER DEFAULT 0,
        allow_overlap INTEGER DEFAULT 0,
        auto_approve INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1
    )
    """)
    
    # Create vacations table with new workflow
    cur.execute("""
    CREATE TABLE IF NOT EXISTS vacations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        type_code TEXT NOT NULL,
        subtype TEXT,
        relation TEXT,
        start_date TEXT NOT NULL,
        end_date TEXT NOT NULL,
        duration INTEGER NOT NULL,
        notes TEXT,
        workflow_state TEXT DEFAULT 'pending_dept' CHECK(workflow_state IN 
            ('pending_dept','pending_manager','approved','rejected','cancelled')),
        rejection_reason TEXT,
        dept_actor_id INTEGER,
        manager_actor_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        dept_decided_at TEXT,
        manager_decided_at TEXT,
        FOREIGN KEY (employee_id) REFERENCES employees(id),
        FOREIGN KEY (type_code) REFERENCES vacation_types(code),
        FOREIGN KEY (dept_actor_id) REFERENCES web_users(id),
        FOREIGN KEY (manager_actor_id) REFERENCES web_users(id)
    )
    """)
    
    # Create absences table with unique constraint
    cur.execute("""
    CREATE TABLE IF NOT EXISTS absences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        type TEXT NOT NULL,
        duration INTEGER DEFAULT 1,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(employee_id, date),
        FOREIGN KEY (employee_id) REFERENCES employees(id)
    )
    """)
    
    # Create accrual_log table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS accrual_log (
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(year, month)
    )
    """)
    
    # Create emergency_reset_log table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS emergency_reset_log (
        year INTEGER PRIMARY KEY,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create audit_log table
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
    
    # Add any missing columns to existing tables (safe alterations)
    try:
        # Check if emergency_vacation_balance exists in employees
        cur.execute("PRAGMA table_info(employees)")
        columns = [row[1] for row in cur.fetchall()]
        
        if 'emergency_vacation_balance' not in columns:
            cur.execute("ALTER TABLE employees ADD COLUMN emergency_vacation_balance INTEGER DEFAULT 12")
            
        if 'initial_vacation_balance' not in columns:
            cur.execute("ALTER TABLE employees ADD COLUMN initial_vacation_balance REAL NULL")
            
        if 'work_pattern' not in columns:
            cur.execute("ALTER TABLE employees ADD COLUMN work_pattern TEXT")
            
        if 'status' not in columns:
            cur.execute("ALTER TABLE employees ADD COLUMN status TEXT DEFAULT 'active'")
            
    except Exception as e:
        logger.warning(f"Could not add missing columns: {e}")
    
    # Create indexes
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_employees_department_id ON employees(department_id)",
        "CREATE INDEX IF NOT EXISTS idx_employees_national_id ON employees(national_id)",
        "CREATE INDEX IF NOT EXISTS idx_employees_serial_number ON employees(serial_number)",
        "CREATE INDEX IF NOT EXISTS idx_vacations_employee_id ON vacations(employee_id)",
        "CREATE INDEX IF NOT EXISTS idx_vacations_workflow_state ON vacations(workflow_state)",
        "CREATE INDEX IF NOT EXISTS idx_absences_employee_date ON absences(employee_id, date)",
    ]
    
    for index_sql in indexes:
        try:
            cur.execute(index_sql)
        except Exception as e:
            logger.warning(f"Could not create index: {e}")
    
    # Seed default data
    _seed_default_data(cur)
    
    conn.commit()
    logger.info("تم تهيئة قاعدة البيانات بنجاح")


def _seed_default_data(cur):
    """Seed default data (departments, admin user, vacation types)."""
    
    # Seed default departments if empty
    cur.execute("SELECT COUNT(*) FROM departments")
    if cur.fetchone()[0] == 0:
        default_departments = [
            'الإدارة', 'الشؤون الادارية', 'الشؤون الطبية', 'التحاليل',
            'الصيدلة', 'التمريض', 'التطعيمات', 'الاسنان'
        ]
        for dept_name in default_departments:
            cur.execute("INSERT INTO departments (name) VALUES (?)", (dept_name,))
    
    # Seed default admin user if no manager exists
    cur.execute("SELECT COUNT(*) FROM web_users WHERE role = 'manager'")
    if cur.fetchone()[0] == 0:
        admin_password_hash = bcrypt.hash("admin123")
        cur.execute("""
            INSERT INTO web_users (username, password_hash, role, is_active)
            VALUES (?, ?, 'manager', 1)
        """, ("admin", admin_password_hash))
    
    # Seed vacation types if empty
    cur.execute("SELECT COUNT(*) FROM vacation_types")
    if cur.fetchone()[0] == 0:
        vacation_types = [
            ('annual', 'سنوية', 1, 0, None, None, None, None, 0, 0, 0, 1),
            ('emergency', 'طارئة', 0, 1, None, 3, 12, None, 0, 0, 0, 1),
            ('maternity_single', 'وضع - عادي', 0, 0, 98, None, None, None, 1, 0, 0, 1),
            ('maternity_twins', 'وضع - توأم', 0, 0, 112, None, None, None, 1, 0, 0, 1),
            ('marriage', 'زواج', 0, 0, 14, None, None, 1, 0, 0, 0, 1),
            ('hajj', 'حج', 0, 0, 20, None, None, 1, 0, 0, 0, 1),
            ('bereavement_d1', 'وفاة درجة أولى', 0, 0, 7, None, None, None, 0, 0, 0, 1),
            ('bereavement_d2', 'وفاة درجة ثانية', 0, 0, 3, None, None, None, 0, 0, 0, 1),
            ('sick', 'مرضية', 0, 0, None, None, None, None, 1, 0, 0, 1),
        ]
        
        cur.executemany("""
            INSERT INTO vacation_types 
            (code, name_ar, deduct_main_balance, uses_emergency_balance, fixed_duration,
             max_days_per_request, yearly_quota, lifetime_quota, requires_docs,
             allow_overlap, auto_approve, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, vacation_types)