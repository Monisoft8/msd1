"""Application factory for the Employee Management System."""
import logging
from flask import Flask, redirect, url_for
from msd.extensions import login_manager
from msd.auth.service import load_user_by_id
from msd.auth.routes import auth_bp
from msd.database.schema_init import init_database
from msd.vacations.accrual_service import run_monthly_accrual
from msd.vacations.emergency_reset_service import run_emergency_reset

logger = logging.getLogger(__name__)


def create_app(config_class="config.Config"):
    """Create and configure the Flask application."""
    # Create Flask app with templates in the root directory
    app = Flask(__name__, template_folder="../")
    
    # Load configuration
    app.config.from_object(config_class)
    
    # Initialize extensions
    login_manager.init_app(app)
    
    # Set up user loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return load_user_by_id(user_id)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    
    # Add root route that redirects to login
    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))
    
    # Initialize database and run services
    with app.app_context():
        try:
            # Initialize database schema
            init_database()
            
            # Run vacation services (idempotent)
            try:
                run_monthly_accrual()
            except Exception as e:
                logger.warning(f"Monthly accrual service error: {e}")
            
            try:
                run_emergency_reset()
            except Exception as e:
                logger.warning(f"Emergency reset service error: {e}")
                
        except Exception as e:
            logger.error(f"Error during application initialization: {e}")
            # Don't fail the app start, but log the error
    
    return app