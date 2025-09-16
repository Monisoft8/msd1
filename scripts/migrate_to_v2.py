#!/usr/bin/env python3
"""
Migration script to upgrade existing employees.db to v2 schema.
This script is idempotent and safe to run multiple times.
"""

import os
import sys
import sqlite3
import shutil
import logging
from datetime import datetime

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from msd.database.schema_init import init_database

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "employees.db")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backups")


def create_backup():
    """Create a backup of the existing database."""
    if not os.path.exists(DB_PATH):
        logger.info("No existing database found, skipping backup")
        return None
    
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"employees_backup_{timestamp}.db")
    
    try:
        shutil.copy2(DB_PATH, backup_path)
        logger.info(f"Database backup created: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise


def migrate_legacy_data():
    """Migrate legacy data to new schema format."""
    if not os.path.exists(DB_PATH):
        logger.info("No existing database found, creating new one")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    try:
        # Check if we have legacy data that needs migration
        tables = []
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        for row in cur.fetchall():
            tables.append(row[0])
        
        logger.info(f"Found tables: {tables}")
        
        # Initialize employees.initial_vacation_balance if NULL
        if 'employees' in tables:
            cur.execute("""
                UPDATE employees 
                SET initial_vacation_balance = vacation_balance 
                WHERE initial_vacation_balance IS NULL
            """)
            affected = cur.rowcount
            if affected > 0:
                logger.info(f"Initialized initial_vacation_balance for {affected} employees")
        
        # Migrate departments if we have legacy text department column
        if 'employees' in tables:
            # Check if employees has a text 'department' column
            cur.execute("PRAGMA table_info(employees)")
            columns = {row[1]: row[2] for row in cur.fetchall()}
            
            if 'department' in columns and columns['department'].upper() == 'TEXT':
                logger.info("Found legacy text department column, migrating...")
                
                # Get unique department names
                cur.execute("SELECT DISTINCT department FROM employees WHERE department IS NOT NULL AND department != ''")
                legacy_departments = [row[0] for row in cur.fetchall()]
                
                for dept_name in legacy_departments:
                    # Insert department if not exists
                    cur.execute("INSERT OR IGNORE INTO departments (name) VALUES (?)", (dept_name,))
                    
                    # Get department ID
                    cur.execute("SELECT id FROM departments WHERE name = ?", (dept_name,))
                    dept_id = cur.fetchone()["id"]
                    
                    # Update employees with department_id
                    cur.execute("""
                        UPDATE employees 
                        SET department_id = ? 
                        WHERE department = ? AND (department_id IS NULL OR department_id = 0)
                    """, (dept_id, dept_name))
                
                logger.info(f"Migrated {len(legacy_departments)} departments")
        
        # Migrate vacation workflow states if we have legacy columns
        if 'vacations' in tables:
            cur.execute("PRAGMA table_info(vacations)")
            columns = [row[1] for row in cur.fetchall()]
            
            if 'status' in columns and 'dept_approval' in columns:
                logger.info("Found legacy vacation approval columns, migrating workflow states...")
                
                # Migrate workflow states based on legacy approval columns
                mappings = [
                    ("'تحت الإجراء'", "dept_approval", "'pending_dept'"),
                    ("'موافق'", "status", "'pending_manager'", "AND dept_approval = 'موافق'"),
                    ("'موافق'", "status", "'approved'", "AND manager_approval = 'موافق'"),
                    ("'approved'", "status", "'approved'"),
                    ("'مرفوض'", "status", "'rejected'"),
                    ("'rejected'", "status", "'rejected'"),
                    ("'مرفوض'", "dept_approval", "'rejected'"),
                ]
                
                # Simple migration for most common cases
                cur.execute("""
                    UPDATE vacations 
                    SET workflow_state = 'pending_dept'
                    WHERE dept_approval = 'تحت الإجراء' OR dept_approval = 'pending'
                """)
                
                cur.execute("""
                    UPDATE vacations 
                    SET workflow_state = 'pending_manager'
                    WHERE dept_approval = 'موافق' AND (status = 'تحت الإجراء' OR status = 'pending')
                """)
                
                cur.execute("""
                    UPDATE vacations 
                    SET workflow_state = 'approved'
                    WHERE status IN ('موافق', 'approved')
                """)
                
                cur.execute("""
                    UPDATE vacations 
                    SET workflow_state = 'rejected'
                    WHERE status IN ('مرفوض', 'rejected') OR dept_approval = 'مرفوض'
                """)
                
                logger.info("Migrated vacation workflow states")
        
        # Map vacation types if we have legacy type text and type_code column exists
        if 'vacations' in tables:
            cur.execute("PRAGMA table_info(vacations)")
            vacation_columns = [row[1] for row in cur.fetchall()]
            
            if 'type' in vacation_columns and 'type_code' in vacation_columns:
                type_mappings = {
                    'سنوية': 'annual',
                    'طارئة': 'emergency',
                    'وضع': 'maternity_single',
                    'زواج': 'marriage',
                    'حج': 'hajj',
                    'وفاة': 'bereavement_d1',
                    'مرضية': 'sick'
                }
                
                for arabic_type, code in type_mappings.items():
                    cur.execute("""
                        UPDATE vacations 
                        SET type_code = ?
                        WHERE type = ? AND (type_code IS NULL OR type_code = '')
                    """, (code, arabic_type))
        
        conn.commit()
        logger.info("Legacy data migration completed successfully")
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error during migration: {e}")
        raise
    finally:
        conn.close()


def main():
    """Main migration function."""
    logger.info("Starting migration to v2 schema...")
    
    # Create backup
    backup_path = create_backup()
    
    try:
        # First run the new schema initialization (idempotent)
        logger.info("Initializing new schema...")
        
        # We need to mock the Flask app context for the schema init
        class MockApp:
            config = {"DB_PATH": DB_PATH}
        
        class MockCurrentApp:
            def __init__(self):
                self.config = {"DB_PATH": DB_PATH}
        
        # Temporarily replace current_app for schema_init
        import msd.database.connection
        original_current_app = getattr(msd.database.connection, 'current_app', None)
        msd.database.connection.current_app = MockCurrentApp()
        
        try:
            init_database()
        finally:
            if original_current_app:
                msd.database.connection.current_app = original_current_app
        
        # Then migrate existing data
        logger.info("Migrating legacy data...")
        migrate_legacy_data()
        
        logger.info("Migration completed successfully!")
        logger.info(f"Backup available at: {backup_path}")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        if backup_path and os.path.exists(backup_path):
            logger.info(f"You can restore from backup: {backup_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()