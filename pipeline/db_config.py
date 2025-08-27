# db_config.py

server = "localhost,1433"
database = "NextDB"
username = "sa"
password = "YourStrong!Passw0rd"

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    f"SERVER={server};DATABASE={database};UID={username};PWD={password}"
)
