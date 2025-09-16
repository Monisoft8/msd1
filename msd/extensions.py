"""Flask extensions initialization."""
from flask_login import LoginManager

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = "auth.login"

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    from msd.auth.service import load_user_by_id
    return load_user_by_id(user_id)