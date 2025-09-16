# msd/employees/routes.py
"""
Employees routes blueprint
"""

from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

from .service import get_all_employees, get_departments, create_employee
from .import_service import import_employees_from_excel


employees_bp = Blueprint("employees", __name__, url_prefix="")


def require_manager(f):
    """Decorator to require manager role"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json:
                return jsonify({"error": "غير مصرح"}), 403
            return "غير مصرح", 403
        
        if current_user.role != "manager":
            if request.is_json:
                return jsonify({"error": "غير مصرح"}), 403
            return "غير مصرح", 403
        
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


@employees_bp.route("/employees")
@login_required
@require_manager
def employees_list():
    """GET /employees: manager-only, fetch all employees joined with departments"""
    employees = get_all_employees()
    departments = get_departments()
    return render_template("employees.html", employees=employees, departments=departments)


@employees_bp.route("/employees/add", methods=["POST"])
@login_required
@require_manager
def add_employee():
    """POST /employees/add: manager-only, accept JSON or form, validate and create employee"""
    try:
        # Accept both JSON and form data
        data = request.get_json() or request.form.to_dict()
        
        # Create employee
        employee_id = create_employee(data)
        
        if request.is_json:
            return jsonify({
                "success": True, 
                "message": "تم إضافة الموظف بنجاح",
                "employee_id": employee_id
            })
        else:
            flash("تم إضافة الموظف بنجاح", "success")
            return redirect(url_for("employees.employees_list"))
            
    except ValueError as e:
        if request.is_json:
            return jsonify({"success": False, "message": str(e)}), 400
        else:
            flash(str(e), "danger")
            return redirect(url_for("employees.employees_list"))
    except Exception as e:
        if request.is_json:
            return jsonify({"success": False, "message": "خطأ في إضافة الموظف"}), 500
        else:
            flash("خطأ في إضافة الموظف", "danger")
            return redirect(url_for("employees.employees_list"))


@employees_bp.route("/import/employees", methods=["POST"])
@login_required
@require_manager
def import_employees():
    """POST /import/employees: Enhanced Excel import with dry-run support"""
    if 'file' not in request.files:
        if request.is_json:
            return jsonify({"success": False, "message": "لم يتم اختيار ملف"}), 400
        flash("لم يتم اختيار ملف", "danger")
        return redirect(url_for("employees.employees_list"))
    
    file = request.files['file']
    if file.filename == '':
        if request.is_json:
            return jsonify({"success": False, "message": "لم يتم اختيار ملف"}), 400
        flash("لم يتم اختيار ملف", "danger")
        return redirect(url_for("employees.employees_list"))
    
    # Check for dry run
    dry_run = request.args.get('dry_run') == '1' or request.form.get('dry_run') == '1'
    create_departments = request.args.get('create_departments', 'true').lower() == 'true'
    
    try:
        # Import employees from Excel
        result = import_employees_from_excel(
            file.stream, 
            dry_run=dry_run,
            create_departments=create_departments
        )
        
        if request.is_json:
            return jsonify({
                "success": True,
                "dry_run": dry_run,
                **result
            })
        else:
            if dry_run:
                flash(f"معاينة الاستيراد: {result['inserted']} موظف جديد، {result['updated']} موظف محدث، {len(result['errors'])} خطأ", "info")
            else:
                flash(f"تم استيراد {result['inserted']} موظف جديد وتحديث {result['updated']} موظف. عدد الأخطاء: {len(result['errors'])}", "success")
            
            return redirect(url_for("employees.employees_list"))
            
    except Exception as e:
        if request.is_json:
            return jsonify({"success": False, "message": f"خطأ في الاستيراد: {str(e)}"}), 500
        flash(f"خطأ في الاستيراد: {str(e)}", "danger")
        return redirect(url_for("employees.employees_list"))