"""Optional Airflow DAG for pipeline A (not needed for the MVP: GitHub Actions / CLI suffice)."""

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG("next_bh_data_rag", start_date=datetime(2026, 1, 1), schedule=None, catchup=False,
         tags=["next-bh", "rag"]) as dag:
    # triggered on a new document version or manually; no promotion without --promote
    BashOperator(task_id="data_rag_pipeline", bash_command="cd {{ var.value.nextbh_repo }} && python -m mlops.data_rag.run")
