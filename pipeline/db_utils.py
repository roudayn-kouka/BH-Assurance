# db_utils.py
import pyodbc
from db_config import conn_str

def get_connection():
    """Create a new database connection."""
    return pyodbc.connect(conn_str, timeout=5)
