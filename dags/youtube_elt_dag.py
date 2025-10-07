from __future__ import annotations

import pendulum
from datetime import timedelta

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.trigger_rule import TriggerRule

default_args = {
    'owner': 'airflow',
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(minutes=30),
    'email_on_failure': True,
    'email_on_retry': True,
}

with DAG(
    dag_id="youtube_elt",
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    schedule="0 0 * * *",  # Run daily at midnight
    max_active_runs=1,
    dagrun_timeout=timedelta(hours=1),
    tags=["youtube", "elt", "json"],
    default_args=default_args,
    doc_md="""
# YouTube Data ETL Pipeline

This DAG extracts video data from a YouTube channel and saves it as JSON.

## Tasks
1. validate_env - Check environment variables
2. fetch_videos - Run YouTube ELT script
3. data_quality - Run data quality checks
4. cleanup - Clean up old files

## Schedule
Runs daily at midnight UTC
""",
) as dag:
    # Start task
    start = EmptyOperator(task_id="start")
    
    # Validate environment variables
    validate_env = BashOperator(
        task_id="validate_env",
        bash_command='python -c "from include.scripts.youtube_elt import load_environment; load_environment()"',
    )
    
    # Run YouTube ELT script
    fetch_videos = BashOperator(
        task_id="fetch_videos",
        bash_command="python /usr/local/airflow/include/scripts/youtube_elt.py",
        execution_timeout=timedelta(minutes=30),
    )
    
    # Data quality check
    data_quality = BashOperator(
        task_id="data_quality",
        bash_command="soda scan -d postgres_db -c /usr/local/airflow/include/soda/configuration.yml /usr/local/airflow/include/soda/checks/videos.yml",
        execution_timeout=timedelta(minutes=10),
    )
    
    # Cleanup task
    cleanup = BashOperator(
        task_id="cleanup",
        bash_command='python -c "from include.scripts.youtube_elt import cleanup_old_files; cleanup_old_files(\\"/usr/local/airflow/data/json\\", 7)"',
        trigger_rule=TriggerRule.ALL_DONE,  # Run even if upstream tasks fail
    )
    
    # End task
    end = EmptyOperator(task_id="end")
    
    # Define task dependencies
    start >> validate_env >> fetch_videos >> data_quality >> cleanup >> end