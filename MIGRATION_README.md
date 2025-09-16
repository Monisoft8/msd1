# Employee Management System - Migration Guide

## Overview
This system has been migrated to a modular Flask architecture with a comprehensive database schema to support vacation management, employee tracking, and workflow automation.

## Migration to v2 Schema

### Running the Migration
To upgrade an existing database to the new v2 schema:

```bash
python scripts/migrate_to_v2.py
```

### What the Migration Does
- **Creates automatic backup**: Saves existing database to `backups/` with timestamp
- **Adds new tables**: vacation_types, employee_work_days, accrual_log, emergency_reset_log
- **Adds new columns**: emergency_vacation_balance, initial_vacation_balance, work_pattern, status to employees
- **Migrates legacy data**: 
  - Maps text department names to department_id relationships
  - Converts old vacation approval columns to new workflow_state system
  - Maps Arabic vacation types to standardized codes
- **Seeds default data**: vacation types, departments, admin user if missing

### Default Login
After migration, you can log in with:
- **Username**: admin
- **Password**: admin123
- **Role**: manager

### New Features
- **Monthly Vacation Accrual**: Automatically runs to add vacation days based on years of service
- **Emergency Balance Reset**: Resets emergency vacation balance to 12 days on January 1st
- **Workflow Management**: New vacation approval workflow with department and manager stages
- **Audit Logging**: Tracks all changes for compliance

### Safety Features
- Migration is **idempotent** - safe to run multiple times
- Creates **filesystem backup** before any changes
- All operations use **database transactions**
- **Preserves existing data** - no data loss

### Troubleshooting
If migration fails, restore from the backup file:
```bash
cp backups/employees_backup_YYYYMMDD_HHMMSS.db employees.db
```

## Running the Application
```bash
python app.py
```

The application will:
1. Initialize the database schema if needed
2. Run vacation accrual service (if due)
3. Run emergency reset service (if January 1st)
4. Start the Flask development server on http://localhost:5000