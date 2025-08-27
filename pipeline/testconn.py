import pyodbc

server = "localhost,1433"
database = "NextDB"
username = "sa"
password = "YourStrong!Passw0rd"

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={server};DATABASE={database};UID={username};PWD={password}"
)

try:
    conn = pyodbc.connect(conn_str, timeout=5)
    print("✅ Connection successful!")
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 5 * FROM test_pp")
    for row in cursor.fetchall():
        print(row)
except Exception as e:
    print("❌ Connection failed:", e)
