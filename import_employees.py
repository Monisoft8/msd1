import pandas as pd
import sqlite3

# تحميل بيانات الموظفين من الإكسل
df = pd.read_excel("employees_data.xlsx")

# الاتصال بقاعدة البيانات
conn = sqlite3.connect("employee_system.db")
cur = conn.cursor()

# إنشاء جدول employees إذا غير موجود
cur.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    national_id TEXT,
    auto_id TEXT,
    name TEXT NOT NULL,
    grade TEXT,
    allowance TEXT,
    grade_date TEXT,
    hire_date TEXT,
    department_id INTEGER
)
""")

# إدخال البيانات من ملف الإكسل
for _, row in df.iterrows():
    cur.execute("""
        INSERT INTO employees (national_id, auto_id, name, grade, allowance, grade_date, hire_date, department_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        str(row.get("الرقم الوطني", "")),
        str(row.get("الرقم الآلي", "")),
        row.get("الاسم", ""),
        row.get("الدرجة", ""),
        str(row.get("العلاوة", "")),
        str(row.get("تاريخ الدرجة", "")),
        str(row.get("تاريخ التعيين", "")),
        None  # ممكن نربطها لاحقًا بالأقسام
    ))

conn.commit()
conn.close()

print("تم استيراد بيانات الموظفين من الإكسل بنجاح ✅")
