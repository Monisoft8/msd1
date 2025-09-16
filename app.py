# app.py
# Employee Management System - Updated with modular structure
# Uses application factory pattern for better organization

import os
import sys
import logging
from msd import create_app

# توجيه stdout إلى stderr ليتوافق مع بيئات معينة
sys.stdout = sys.stderr

# إعداد logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create app using factory
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)