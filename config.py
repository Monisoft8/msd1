"""Configuration for the Employee Management System."""
import os


class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get("EMP_SYS_SECRET") or "change_this_secret_12345"
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "employees.db")
    EXPORT_DIR = "static/exports"
    MAX_IMPORT_ROWS = 5000