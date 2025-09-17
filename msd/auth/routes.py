"""Authentication routes."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from passlib.hash import bcrypt
from msd.auth.service import find_user_by_username, WebUser

auth_bp = Blueprint('auth', __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Login route."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user_row = find_user_by_username(username)
        if user_row and bcrypt.verify(password, user_row["password_hash"]):
            user = WebUser(user_row["id"], user_row["username"], user_row["role"],
                          user_row["department_id"], user_row["dept_name"])
            login_user(user)
            # For now, redirect to a simple success page since other routes aren't moved yet
            logout_url = url_for('auth.logout')
            return f"""
            <h1>تم تسجيل الدخول بنجاح!</h1>
            <p>مرحباً {user.username}</p>
            <p>الدور: {user.role}</p>
            <p>القسم: {user.dept_name or 'غير محدد'}</p>
            <a href="{logout_url}">تسجيل الخروج</a>
            """
        flash("اسم المستخدم أو كلمة المرور غير صحيحة", "danger")

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Logout route."""
    logout_user()
    return redirect(url_for("auth.login"))