# msd/auth.py
"""
Authentication utilities for MSD Employee Management System
"""

from .database.connection import get_conn, WebUser


def find_user_by_username(username):
    """Find user by username in web_users table"""
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


def load_user(user_id):
    """User loader for Flask-Login"""
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