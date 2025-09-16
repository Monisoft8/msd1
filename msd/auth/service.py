"""Authentication service and user models."""
from flask_login import UserMixin
from passlib.hash import bcrypt
from msd.database.connection import get_conn


class WebUser(UserMixin):
    """User model for Flask-Login."""
    
    def __init__(self, id, username, role, dept_id=None, dept_name=None):
        # id as str for Flask-Login compatibility
        self.id = str(id)
        self.username = username
        self.role = role
        self.dept_id = dept_id
        self.dept_name = dept_name


def find_user_by_username(username):
    """Find user by username."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT wu.id, wu.username, wu.role, wu.password_hash, wu.department_id, d.name as dept_name
        FROM web_users wu 
        LEFT JOIN departments d ON wu.department_id = d.id 
        WHERE wu.username = ?
    """, (username,))
    result = cur.fetchone()
    conn.close()
    return result


def load_user_by_id(user_id):
    """Load user by ID for Flask-Login."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT wu.id, wu.username, wu.role, wu.department_id, d.name as dept_name
        FROM web_users wu 
        LEFT JOIN departments d ON wu.department_id = d.id 
        WHERE wu.id = ?
    """, (user_id,))
    result = cur.fetchone()
    conn.close()
    if not result:
        return None
    return WebUser(result["id"], result["username"], result["role"], 
                  result["department_id"], result["dept_name"])