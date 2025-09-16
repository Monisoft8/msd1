#!/usr/bin/env python3
# create_sample_excel.py - Create sample Excel file for testing

import pandas as pd
from datetime import datetime

# Sample employee data with both English and Arabic column names
sample_data = {
    'serial_number': ['001', '002', '003'],
    'name': ['أحمد محمد', 'فاطمة علي', 'محمد سعد'],
    'national_id': ['123456789012', '234567890123', '345678901234'], 
    'department': ['الإدارة', 'المالية', 'التقنية'],
    'job_grade': ['مدير', 'محاسب', 'مطور'],
    'hiring_date': ['2023-01-15', '2023-02-20', '2023-03-10'],
    'grade_date': ['2023-01-15', '2023-02-20', '2023-03-10'],
    'bonus': [1000, 800, 1200],
    'vacation_balance': [30, 28, 32],
    'work_days': ['السبت-الخميس', 'السبت-الخميس', 'الأحد-الخميس']
}

# Create DataFrame and save as Excel
df = pd.DataFrame(sample_data)
df.to_excel('/home/runner/work/msd1/msd1/sample_employees.xlsx', index=False)

print("Sample Excel file created successfully!")
print("Columns:", list(df.columns))
print("Data:")
print(df)

# Also create one with Arabic columns
arabic_data = {
    'الرقم الآلي': ['004', '005'],
    'الاسم': ['سارة أحمد', 'علي محمد'],
    'الرقم الوطني': ['456789012345', '567890123456'],
    'القسم': ['الموارد البشرية', 'الإدارة'],
    'الدرجة الوظيفية': ['أخصائي', 'مدير مساعد'],
    'تاريخ التعيين': ['2023-04-01', '2023-05-15'],
    'تاريخ الدرجة': ['2023-04-01', '2023-05-15'],
    'العلاوة': [900, 1100],
    'رصيد الإجازات': [25, 30],
    'أيام العمل': ['السبت-الخميس', 'السبت-الخميس']
}

df_arabic = pd.DataFrame(arabic_data)
df_arabic.to_excel('/home/runner/work/msd1/msd1/sample_employees_arabic.xlsx', index=False)

print("\nArabic columns Excel file created successfully!")
print("Arabic columns:", list(df_arabic.columns))