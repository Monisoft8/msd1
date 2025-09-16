#!/usr/bin/env python3
# debug_import.py - Debug the import process
import pandas as pd
import sys
sys.path.append('/home/runner/work/msd1/msd1')

from msd.employees.import_service import import_employees_from_excel

# Test import with detailed logging
print("Testing import with detailed error reporting...")

try:
    with open('/home/runner/work/msd1/msd1/sample_employees_arabic.xlsx', 'rb') as f:
        result = import_employees_from_excel(f, dry_run=True, create_departments=True)
        
    print("Import result:")
    print(f"Inserted: {result['inserted']}")
    print(f"Updated: {result['updated']}")
    print(f"Errors: {len(result['errors'])}")
    
    if result['errors']:
        print("\nDetailed errors:")
        for error in result['errors']:
            print(f"Row {error['row']}: {error['reason']}")
    
except Exception as e:
    print(f"Import failed with exception: {e}")
    import traceback
    traceback.print_exc()