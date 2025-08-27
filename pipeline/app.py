# app.py
from fastapi import FastAPI
import pandas as pd
from pipeline.db_utils import get_connection


app = FastAPI()

@app.get("/tables")
def list_tables():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE'")
        tables = [row[0] for row in cursor.fetchall()]
    return {"tables": tables}

@app.get("/read/{table_name}")
def read_table(table_name: str):
    with get_connection() as conn:
        df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
    return {"data": df.to_dict(orient="records")}

@app.post("/execute_sql/")
def execute_sql(query: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
    return {"status": "success", "executed": query}

@app.get("/")
def root():
    return {"message": "FastAPI + SQL Server is running 🚀"}

@app.get("/top5")
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
