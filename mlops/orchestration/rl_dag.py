"""Optional Airflow DAG for pipeline B. Scheduled weekly; promotion stays a manual gate."""

from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG("next_bh_rl", start_date=datetime(2026, 1, 1), schedule="@weekly", catchup=False,
         tags=["next-bh", "rl"]) as dag:
    export = BashOperator(
        task_id="export_events",
        bash_command="cd {{ var.value.nextbh_repo }} && python -m mlops.rl.export_events --kafka-topic decision_events --bootstrap {{ var.value.kafka_bootstrap }}",
    )
    train_eval_publish = BashOperator(
        task_id="train_evaluate_publish",
        bash_command="cd {{ var.value.nextbh_repo }} && python -m mlops.rl.run",
    )
    export >> train_eval_publish
