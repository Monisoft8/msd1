from flask import Flask, redirect, url_for
from .extensions import login_manager

def create_app(config_class="config.Config"):
    app = Flask(__name__)

    # تحميل الإعدادات
    try:
        if isinstance(config_class, str):
            if "." in config_class:
                module, _, cls = config_class.rpartition(".")
                mod = __import__(module, fromlist=[cls])
                app.config.from_object(getattr(mod, cls))
            else:
                import config as cfg
                app.config.from_object(getattr(cfg, config_class, cfg.Config))
        else:
            app.config.from_object(config_class)
    except Exception as e:
        app.logger.warning(f"Config load warning: {e}")

    # تهيئة تسجيل الدخول
    login_manager.init_app(app)

    # تهيئة قاعدة البيانات/المخطط
    try:
        from .database.schema_init import init_database
        with app.app_context():
            init_database()
    except Exception as e:
        app.logger.warning(f"Database init skipped/failed: {e}")

    # تسجيل Blueprints
    try:
        from .auth.routes import auth_bp
        app.register_blueprint(auth_bp)
    except Exception as e:
        app.logger.warning(f"Auth blueprint not registered: {e}")

    try:
        from .employees.routes import employees_bp
        app.register_blueprint(employees_bp)
    except Exception:
        # إن لم تكن وحدة الموظفين متاحة بعد، لا نوقف التطبيق
        pass

    # خدمات تلقائية (تراكم/إعادة ضبط) — غير معطِّلة للتشغيل
    try:
        from .vacations.accrual_service import run_monthly_accrual
        from .vacations.emergency_reset_service import run_annual_reset
        with app.app_context():
            try:
                run_monthly_accrual()
            except Exception as e:
                app.logger.info(f"Accrual service skipped: {e}")
            try:
                run_annual_reset()
            except Exception as e:
                app.logger.info(f"Emergency reset skipped: {e}")
    except Exception:
        # الخدمات اختيارية
        pass

    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    return app
