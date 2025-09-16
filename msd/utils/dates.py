"""Date utility functions."""
from datetime import datetime, date


def calculate_inclusive_days(start_date_str, end_date_str):
    """
    Calculate inclusive day span between two ISO dates (YYYY-MM-DD).
    
    Args:
        start_date_str: Start date in YYYY-MM-DD format
        end_date_str: End date in YYYY-MM-DD format
        
    Returns:
        int: Number of days inclusive (start..end)
    """
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        
        # Calculate inclusive days
        delta = (end_date - start_date).days + 1
        return max(0, delta)  # Ensure non-negative result
        
    except ValueError as e:
        raise ValueError(f"Invalid date format. Expected YYYY-MM-DD: {e}")


def is_valid_date_range(start_date_str, end_date_str):
    """
    Check if date range is valid (start <= end).
    
    Args:
        start_date_str: Start date in YYYY-MM-DD format
        end_date_str: End date in YYYY-MM-DD format
        
    Returns:
        bool: True if valid range
    """
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        return start_date <= end_date
    except ValueError:
        return False