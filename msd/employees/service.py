# msd/employees/service.py
"""
Employee service layer for database operations
"""

from ..database.connection import get_conn


def get_all_employees():
    """Get all employees joined with departments"""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT e.*, d.name as dept_name 
        FROM employees e 
        LEFT JOIN departments d ON e.department_id = d.id
        ORDER BY e.name
    """)
    employees = cur.fetchall()
    conn.close()
    return employees


def get_departments():
    """Get all departments"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM departments ORDER BY name")
    departments = cur.fetchall()
    conn.close()
    return departments


def create_employee(employee_data):
    """Create a new employee record"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Validate required fields
    if not employee_data.get('name'):
        raise ValueError("اسم الموظف مطلوب")
    
    national_id = str(employee_data.get('national_id', '')).strip()
    if not national_id:
        raise ValueError("الرقم الوطني مطلوب")
    
    if len(national_id) != 12 or not national_id.isdigit():
        raise ValueError("الرقم الوطني يجب أن يكون 12 رقماً")
    
    try:
        cur.execute("""
            INSERT INTO employees (serial_number, name, national_id, department_id, job_grade, 
                                 hiring_date, grade_date, bonus, vacation_balance, work_pattern)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            employee_data.get('serial_number'),
            employee_data.get('name'),
            national_id,
            employee_data.get('department_id'),
            employee_data.get('job_grade'),
            employee_data.get('hiring_date'),
            employee_data.get('grade_date'),
            employee_data.get('bonus', 0),
            employee_data.get('vacation_balance', 30),
            employee_data.get('work_pattern')
        ))
        
        employee_id = cur.lastrowid
        conn.commit()
        conn.close()
        return employee_id
        
    except Exception as e:
        conn.close()
        raise e


def get_employee_by_national_id(national_id):
    """Get employee by national ID"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM employees WHERE national_id = ?", (national_id,))
    employee = cur.fetchone()
    conn.close()
    return employee


def update_employee(employee_id, employee_data):
    """Update existing employee record"""
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            UPDATE employees 
            SET serial_number=?, name=?, national_id=?, department_id=?, job_grade=?, 
                hiring_date=?, grade_date=?, bonus=?, vacation_balance=?, work_pattern=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
        """, (
            employee_data.get('serial_number'),
            employee_data.get('name'),
            employee_data.get('national_id'),
            employee_data.get('department_id'),
            employee_data.get('job_grade'),
            employee_data.get('hiring_date'),
            employee_data.get('grade_date'),
            employee_data.get('bonus', 0),
            employee_data.get('vacation_balance', 30),
            employee_data.get('work_pattern'),
            employee_id
        ))
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        conn.close()
        raise e


def get_or_create_department(dept_name):
    """Get department ID or create new department"""
    if not dept_name or not dept_name.strip():
        return None
        
    conn = get_conn()
    cur = conn.cursor()
    
    # Try to find existing department
    cur.execute("SELECT id FROM departments WHERE name = ?", (dept_name.strip(),))
    result = cur.fetchone()
    
    if result:
        conn.close()
        return result["id"]
    
    # Create new department
    cur.execute("INSERT INTO departments (name) VALUES (?)", (dept_name.strip(),))
    dept_id = cur.lastrowid
    conn.commit()
    conn.close()
    return dept_id