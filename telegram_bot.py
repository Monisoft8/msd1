from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler
)
import logging
from datetime import datetime, timedelta
import sqlite3
from passlib.hash import bcrypt
import os

# Conversation states
(
    PASSWORD, NATIONAL_ID, SERIAL_NUMBER, MAIN_MENU,
    VACATION_TYPE, VACATION_DEATH_TYPE, VACATION_DEATH_RELATION,
    VACATION_DATE, VACATION_DURATION, CONFIRM_REQUEST
) = range(10)

BOT_PASSWORD = "adw2025"

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def execute_query(self, query, params=(), commit=True):
        try:
            self.cursor.execute(query, params)
            if commit:
                self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Database error: {e}")
            return False
    
    def get_employee(self, national_id, serial_number):
        self.execute_query("""
            SELECT id, name, national_id, department_id,
                   job_grade, hiring_date, vacation_balance, emergency_vacation_balance
            FROM employees
            WHERE national_id=? AND serial_number=?
        """, (national_id, serial_number), commit=False)
        return self.cursor.fetchone()
    
    def get_vacation_balance(self, employee_id):
        self.execute_query("""
            SELECT vacation_balance, emergency_vacation_balance
            FROM employees WHERE id=?
        """, (employee_id,), commit=False)
        return self.cursor.fetchone()
    
    def create_vacation_request(self, employee_id, vac_type, start_date, end_date, duration, notes=""):
        return self.execute_query("""
            INSERT INTO vacations (employee_id, type, start_date, end_date, duration, notes, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (employee_id, vac_type, start_date, end_date, duration, notes))
    
    def get_vacation_history(self, employee_id, limit=10):
        self.execute_query("""
            SELECT id, type, start_date, end_date, duration, status, dept_approval
            FROM vacations
            WHERE employee_id = ?
            ORDER BY start_date DESC
            LIMIT ?
        """, (employee_id, limit), commit=False)
        return self.cursor.fetchall()
    
    def cancel_vacation(self, vacation_id, employee_id):
        self.execute_query("""
            UPDATE vacations SET status='cancelled' 
            WHERE id=? AND employee_id=? AND status='pending'
        """, (vacation_id, employee_id))

class EmployeeQueryBot:
    def __init__(self, token, db_manager):
        self.token = token
        self.db = db_manager
        self.setup_handlers()

    def setup_handlers(self):
        self.application = ApplicationBuilder().token(self.token).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.start)],
            states={
                PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.check_password)],
                NATIONAL_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_national_id)],
                SERIAL_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_serial_number)],
                MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_main_menu)],
                VACATION_TYPE: [
                    MessageHandler(filters.Regex("^(سنوية|طارئة|وفاة|حج|زواج|وضع|مرضية|↩️ رجوع|إلغاء)$"), self.handle_vacation_type),
                    MessageHandler(filters.Regex("^(وضع عادي|وضع توأم)$"), self.handle_vacation_subtype)
                ],
                VACATION_DEATH_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vacation_death_type)],
                VACATION_DEATH_RELATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vacation_death_relation)],
                VACATION_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vacation_date_selection)],
                VACATION_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_vacation_duration)],
                CONFIRM_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.confirm_request)]
            },
            fallbacks=[
                CommandHandler('cancel', self.cancel),
                MessageHandler(filters.Regex("^إلغاء$"), self.cancel)
            ],
            allow_reentry=True
        )
        self.application.add_handler(conv_handler)
        self.application.add_error_handler(self.error_handler)

    async def error_handler(self, update, context):
        logger.error(f"حدث خطأ في البوت: {context.error}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "أهلاً بكم في منظومة شؤون الموظفين\n"
            "الرجاء إدخال كلمة المرور:",
            reply_markup=ReplyKeyboardMarkup([["إلغاء"]], resize_keyboard=True)
        )
        return PASSWORD

    async def check_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text != BOT_PASSWORD:
            await update.message.reply_text("كلمة مرور خاطئة، حاول مرة أخرى", reply_markup=ReplyKeyboardMarkup([["إلغاء"]], resize_keyboard=True))
            return PASSWORD
        await update.message.reply_text("الرجاء إدخال الرقم الوطني:", reply_markup=ReplyKeyboardMarkup([["إلغاء"]], resize_keyboard=True))
        return NATIONAL_ID

    async def handle_national_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data['national_id'] = update.message.text
        await update.message.reply_text("الرجاء إدخال الرقم الآلي:", reply_markup=ReplyKeyboardMarkup([["إلغاء"]], resize_keyboard=True))
        return SERIAL_NUMBER

    async def handle_serial_number(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        employee = self.db.get_employee(
            context.user_data['national_id'],
            update.message.text
        )
        if not employee:
            await update.message.reply_text("بيانات غير صحيحة، الرجاء المحاولة مرة أخرى", reply_markup=ReplyKeyboardMarkup([["إلغاء"]], resize_keyboard=True))
            return ConversationHandler.END
        
        context.user_data['employee'] = dict(employee)
        context.user_data['employee_id'] = employee['id']
        await self.show_main_menu(update)
        return MAIN_MENU

    async def show_main_menu(self, update: Update):
        keyboard = [
            ["📅 طلب إجازة", "📝 سجل الغياب"],
            ["📊 الدرجة الوظيفية", "✈️ رصيد الإجازات"],
            ["📋 سجل الإجازات", "📅 أيام العمل"],
            ["👤 بياناتي الأساسية"],
            ["إلغاء"]
        ]
        await update.message.reply_text(
            "اختر الخيار المطلوب:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )

    # ... (استمرار باقي الدوال بنفس المنطق مع التعديلات اللازمة)

    def run(self):
        self.application.run_polling()

# تشغيل البوت
if __name__ == "__main__":
    db_manager = DatabaseManager("employees.db")
    bot = EmployeeQueryBot("YOUR_TELEGRAM_BOT_TOKEN", db_manager)
    bot.run()