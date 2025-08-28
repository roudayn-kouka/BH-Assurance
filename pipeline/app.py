# app.py
from fastapi import FastAPI, Body
from pydantic import BaseModel
import pandas as pd
from db_utils import get_connection

app = FastAPI(
    title="SQL Server API",
    description="API to interact with SQL Server: list tables, read data, and execute queries.",
    version="1.0.0"
)

class SQLQuery(BaseModel):
    query: str

@app.get(
    "/tables",
    summary="List all database tables",
    description="Fetches all table names from the connected SQL Server database."
)
def list_tables():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        tables = [row[0] for row in cursor.fetchall()]
    return {"tables": tables}

@app.get(
    "/read/{table_name}",
    summary="Read table contents",
    description="Fetches all rows from the given table name and returns them as JSON."
)
def read_table(table_name: str):
    with get_connection() as conn:
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    return {"data": df.to_dict(orient="records")}

@app.post(
    "/execute_sql/",
    summary="Execute SQL query",
    description="Executes a raw SQL query (e.g., INSERT, UPDATE, DELETE, CREATE TABLE).",
)
def execute_sql(query: SQLQuery = Body(..., description="SQL query to execute")):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query.query)
        conn.commit()
    return {"status": "success", "executed": query.query}

@app.get(
    "/",
    summary="Root endpoint",
    description="Check if the API is running."
)
def root():
    return {"message": "FastAPI + SQL Server is running 🚀"}

@app.get(
    "/top5",
    summary="Get top 5 rows per table",
    description="Fetches the first 5 rows from each table in the database."
)
def top5_rows():
    results = {}
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            try:
                df = pd.read_sql(f"SELECT TOP 5 * FROM {table}", conn)
                results[table] = df.to_dict(orient="records")
            except Exception as e:
                results[table] = f"❌ Error: {str(e)}"
    return results
