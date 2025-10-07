from __future__ import annotations

import pendulum
from datetime import timedelta

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator
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
    dag_id="produce_json",
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
    
    ## Schedule
    Runs daily at midnight UTC
    
    ## Tasks
    - run_elt_script: Extracts video data using YouTube API
    """,
) as dag:
    # Add monitoring using bash heartbeat
    pre_check = BashOperator(
        task_id="pre_execution_check",
        bash_command='echo "Starting YouTube data extraction process..."',
    )
    
    run_elt = BashOperator(
        task_id="run_elt_script",
        bash_command="python /usr/local/airflow/include/scripts/youtube_elt.py",
        execution_timeout=timedelta(minutes=30),
    )
    
    post_check = BashOperator(
        task_id="post_execution_check",
        bash_command='echo "YouTube data extraction completed successfully"',
        trigger_rule=TriggerRule.ALL_SUCCESS,
    )
    
    pre_check >> run_elt >> post_check