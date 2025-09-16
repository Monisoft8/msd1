"""Flask extensions initialization."""
from flask_login import LoginManager

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = "auth.login"