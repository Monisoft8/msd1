# app_factory.py
"""
Enhanced MSD Employee Management System with modular structure
This file provides the new modular approach while preserving backward compatibility
"""

import os
import sys
import logging
from flask import Flask
from flask_login import LoginManager

# Import the modular components
from msd import create_app
from msd.database.connection import init_database, WebUser
from msd.auth import find_user_by_username, load_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# توجيه stdout إلى stderr ليتوافق مع بيئات معينة
sys.stdout = sys.stderr


def create_enhanced_app():
    """Create Flask app with both modular and legacy routes"""
    
    # Create app using the modular factory
    app = create_app()
    
    # Import and register legacy routes that aren't yet migrated
    from app_legacy import register_legacy_routes
    register_legacy_routes(app)
    
    return app


if __name__ == "__main__":
    app = create_enhanced_app()
    
    # Initialize database if needed
    DB_PATH = os.path.join(os.path.dirname(__file__), "employees.db")
    if not os.path.exists(DB_PATH):
        with app.app_context():
            init_database()
    
    app.run(host="0.0.0.0", port=5000, debug=True)