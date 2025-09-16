# msd/employees/import_service.py
"""
Enhanced Excel import service for employees
"""

import pandas as pd
import logging
from typing import Dict, Any, List, BinaryIO

from ..database.connection import get_conn
from ..utils.excel import (
    normalize_column_names, safe_extract_value, normalize_date,
    validate_national_id, safe_int, safe_float
)
from .service import get_or_create_department, get_employee_by_national_id, update_employee


logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_CONFIG = {
    'MAX_IMPORT_ROWS': 1000,
    'REQUIRED_COLUMNS': ['name', 'national_id'],
    'DEFAULT_VACATION_BALANCE': 30.0
}


def import_employees_from_excel(
    file_stream: BinaryIO, 
    dry_run: bool = False,
    create_departments: bool = True,
    max_rows: int = None
) -> Dict[str, Any]:
    """
    Import employees from Excel file with enhanced validation and reporting
    
    Args:
        file_stream: Excel file stream
        dry_run: If True, validate but don't commit changes
        create_departments: If True, create departments that don't exist
        max_rows: Maximum rows to process (defaults to config)
    
    Returns:
        Dict with keys: inserted, updated, errors
    """
    if max_rows is None:
        max_rows = DEFAULT_CONFIG['MAX_IMPORT_ROWS']
    
    # Read Excel file
    try:
        df = pd.read_excel(file_stream, nrows=max_rows)
    except Exception as e:
        raise ValueError(f"خطأ في قراءة ملف Excel: {str(e)}")
    
    if df.empty:
        raise ValueError("ملف Excel فارغ")
    
    # Normalize column names
    column_mapping = normalize_column_names(df)
    
    if not column_mapping:
        raise ValueError("لم يتم العثور على أعمدة صالحة في الملف")
    
    # Check required columns
    missing_required = []
    for required_col in DEFAULT_CONFIG['REQUIRED_COLUMNS']:
        if required_col not in column_mapping:
            missing_required.append(required_col)
    
    if missing_required:
        raise ValueError(f"أعمدة مطلوبة مفقودة: {', '.join(missing_required)}")
    
    logger.info(f"الأعمدة المطابقة: {column_mapping}")
    
    # Initialize counters and error list
    inserted_count = 0
    updated_count = 0
    errors = []
    
    # Get database connection
    conn = get_conn()
    cur = conn.cursor()
    
    try:
        # Process each row
        for index, row in df.iterrows():
            try:
                # Extract and validate data
                result = _process_employee_row(
                    row, column_mapping, index + 1, create_departments, cur
                )
                
                if result['error']:
                    errors.append({
                        'row': index + 1,
                        'reason': result['error']
                    })
                    continue
                
                employee_data = result['data']
                
                # Check if employee exists (by national_id)
                existing_employee = get_employee_by_national_id(employee_data['national_id'])
                
                if not dry_run:
                    if existing_employee:
                        # Update existing employee
                        _update_existing_employee(existing_employee, employee_data, cur)
                        updated_count += 1
                    else:
                        # Insert new employee
                        _insert_new_employee(employee_data, cur)
                        inserted_count += 1
                else:
                    # Dry run - just count
                    if existing_employee:
                        updated_count += 1
                    else:
                        inserted_count += 1
                        
            except Exception as e:
                errors.append({
                    'row': index + 1,
                    'reason': f"خطأ في معالجة الصف: {str(e)}"
                })
                logger.exception(f"خطأ في الصف {index + 1}")
        
        # Commit changes if not dry run
        if not dry_run:
            conn.commit()
        
    finally:
        conn.close()
    
    return {
        'inserted': inserted_count,
        'updated': updated_count,
        'errors': errors
    }


def _process_employee_row(
    row: pd.Series, 
    column_mapping: Dict[str, str], 
    row_number: int,
    create_departments: bool,
    cursor
) -> Dict[str, Any]:
    """
    Process a single employee row and validate data
    
    Returns:
        Dict with keys: data (employee data dict), error (error message or None)
    """
    try:
        # Extract basic data
        name = safe_extract_value(row, column_mapping.get('name', ''), '').strip()
        if not name:
            return {'error': 'الاسم مطلوب', 'data': None}
        
        # Validate national ID
        national_id_raw = safe_extract_value(row, column_mapping.get('national_id', ''), '')
        is_valid, national_id = validate_national_id(national_id_raw)
        if not is_valid:
            return {'error': f'الرقم الوطني غير صالح: {national_id_raw}', 'data': None}
        
        # Extract other fields
        serial_number = safe_extract_value(row, column_mapping.get('serial_number', ''), '').strip()
        job_grade = safe_extract_value(row, column_mapping.get('job_grade', ''), '').strip()
        
        # Process dates
        hiring_date = normalize_date(safe_extract_value(row, column_mapping.get('hiring_date', ''), ''))
        grade_date = normalize_date(safe_extract_value(row, column_mapping.get('grade_date', ''), ''))
        
        # Process numeric fields
        bonus = safe_int(safe_extract_value(row, column_mapping.get('bonus', ''), 0))
        vacation_balance = safe_float(
            safe_extract_value(row, column_mapping.get('vacation_balance', ''), 
                             DEFAULT_CONFIG['DEFAULT_VACATION_BALANCE'])
        )
        
        # Process work pattern
        work_pattern = safe_extract_value(row, column_mapping.get('work_days', ''), '').strip()
        
        # Handle department
        department_id = None
        department_name = safe_extract_value(row, column_mapping.get('department', ''), '').strip()
        if department_name:
            if create_departments:
                department_id = get_or_create_department(department_name)
            else:
                # Find existing department
                cursor.execute("SELECT id FROM departments WHERE name = ?", (department_name,))
                dept_row = cursor.fetchone()
                if dept_row:
                    department_id = dept_row["id"]
                else:
                    return {'error': f'القسم غير موجود: {department_name}', 'data': None}
        
        # Build employee data
        employee_data = {
            'serial_number': serial_number,
            'name': name,
            'national_id': national_id,
            'department_id': department_id,
            'job_grade': job_grade,
            'hiring_date': hiring_date,
            'grade_date': grade_date,
            'bonus': bonus,
            'vacation_balance': vacation_balance,
            'work_pattern': work_pattern
        }
        
        return {'error': None, 'data': employee_data}
        
    except Exception as e:
        return {'error': f'خطأ في معالجة البيانات: {str(e)}', 'data': None}


def _update_existing_employee(existing_employee, new_data: Dict[str, Any], cursor):
    """
    Update existing employee with new data
    
    Note: Always allow updating vacation_balance per user instruction
    """
    # Prepare update data, preserving initial_vacation_balance if it exists
    update_data = new_data.copy()
    
    # Handle initial_vacation_balance logic
    if existing_employee['initial_vacation_balance'] is None:
        # First time setting initial vacation balance
        update_data['initial_vacation_balance'] = new_data['vacation_balance']
    
    cursor.execute("""
        UPDATE employees 
        SET serial_number=?, name=?, national_id=?, department_id=?, job_grade=?, 
            hiring_date=?, grade_date=?, bonus=?, vacation_balance=?, work_pattern=?,
            initial_vacation_balance=COALESCE(?, initial_vacation_balance),
            updated_at=CURRENT_TIMESTAMP
        WHERE id=?
    """, (
        update_data['serial_number'],
        update_data['name'],
        update_data['national_id'],
        update_data['department_id'],
        update_data['job_grade'],
        update_data['hiring_date'],
        update_data['grade_date'],
        update_data['bonus'],
        update_data['vacation_balance'],
        update_data['work_pattern'],
        update_data.get('initial_vacation_balance'),
        existing_employee['id']
    ))


def _insert_new_employee(employee_data: Dict[str, Any], cursor):
    """
    Insert new employee record
    """
    # Set initial_vacation_balance to vacation_balance for new employees
    employee_data['initial_vacation_balance'] = employee_data['vacation_balance']
    
    cursor.execute("""
        INSERT INTO employees (serial_number, name, national_id, department_id, job_grade, 
                             hiring_date, grade_date, bonus, vacation_balance, initial_vacation_balance, work_pattern)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        employee_data['serial_number'],
        employee_data['name'],
        employee_data['national_id'],
        employee_data['department_id'],
        employee_data['job_grade'],
        employee_data['hiring_date'],
        employee_data['grade_date'],
        employee_data['bonus'],
        employee_data['vacation_balance'],
        employee_data['initial_vacation_balance'],
        employee_data['work_pattern']
    ))