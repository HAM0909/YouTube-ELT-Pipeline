from __future__ import annotations

import pendulum

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator

with DAG(
    dag_id="data_quality",
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    schedule="10 0 * * *",
    tags=["youtube", "elt", "data_quality"],
) as dag:
    start = EmptyOperator(task_id="start")

    # Run Soda scan for data quality checks
    run_soda_scan = BashOperator(
        task_id="run_soda_scan",
        bash_command="soda scan -d postgres_db -c /usr/local/airflow/include/soda/configuration.yml /usr/local/airflow/include/soda/checks/videos.yml",
    )

    end = EmptyOperator(task_id="end")

    # Define task dependencies
    start >> run_soda_scan >> end