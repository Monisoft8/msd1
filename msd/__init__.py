# msd/__init__.py
"""
MSD Employee Management System
Factory pattern for Flask application
"""

import os
from flask import Flask
from flask_login import LoginManager

from .database.connection import init_database


def create_app(config=None):
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = os.environ.get("EMP_SYS_SECRET", "change_this_secret_12345")
    
    if config:
        app.config.update(config)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login"
    
    # Import and register the user loader here to avoid circular imports
    from .auth import load_user
    login_manager.user_loader(load_user)
    
    # Register blueprints
    from .employees.routes import employees_bp
    app.register_blueprint(employees_bp)
    
    # Initialize database on first request
    # Skip initialization for now to avoid conflicts
    # init_database()
    pass
    
    return app