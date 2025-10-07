from __future__ import annotations

import json
import pendulum
from datetime import timedelta

from airflow.models.dag import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

def load_json_to_staging():
    json_file_path = "/usr/local/airflow/data/json/youtube_data.json"
    pg_hook = PostgresHook(postgres_conn_id="postgres_default")
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    with open(json_file_path, 'r') as f:
        data = json.load(f)

    # Handle both direct list and structured data formats
    videos = data.get('videos', data) if isinstance(data, dict) else data
    
    for video in videos:
        cursor.execute(
            """
            INSERT INTO staging.videos (video_id, title, published_at, duration, view_count, like_count, comment_count)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (video_id) DO NOTHING;
            """,
            (
                video.get('id', video.get('video_id')),
                video['title'],
                video['published_at'],
                video['duration'],
                int(video.get('views', video.get('view_count', '0'))),
                int(video.get('likes', video.get('like_count', '0'))),
                int(video.get('comments', video.get('comment_count', '0')))
            )
        )
    conn.commit()
    cursor.close()
    conn.close()

with DAG(
    dag_id="update_db",
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    schedule="5 0 * * *",
    tags=["youtube", "elt", "database"],
) as dag:
    create_schema = PostgresOperator(
        task_id="create_schema",
        postgres_conn_id="postgres_default",
        sql="""
        CREATE SCHEMA IF NOT EXISTS staging;
        CREATE SCHEMA IF NOT EXISTS core;
        """
    )
    
    create_staging_table = PostgresOperator(
        task_id="create_staging_table",
        postgres_conn_id="postgres_default",
        sql="""
        CREATE TABLE IF NOT EXISTS staging.videos (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            published_at TIMESTAMP,
            duration TEXT,
            view_count BIGINT,
            like_count BIGINT,
            comment_count BIGINT
        );
        """
    )

    create_core_table = PostgresOperator(
        task_id="create_core_table",
        postgres_conn_id="postgres_default",
        sql="""
        CREATE TABLE IF NOT EXISTS core.videos (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            published_at TIMESTAMP,
            duration TEXT,
            view_count BIGINT,
            like_count BIGINT,
            comment_count BIGINT,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    load_json_to_staging_task = PythonOperator(
        task_id="load_json_to_staging",
        python_callable=load_json_to_staging,
    )

    transfer_staging_to_core = PostgresOperator(
        task_id="transfer_staging_to_core",
        postgres_conn_id="postgres_default",
        sql="""
        INSERT INTO core.videos (video_id, title, published_at, duration, view_count, like_count, comment_count)
        SELECT video_id, title, published_at, duration, view_count, like_count, comment_count
        FROM staging.videos
        ON CONFLICT (video_id) DO UPDATE SET
            title = EXCLUDED.title,
            published_at = EXCLUDED.published_at,
            duration = EXCLUDED.duration,
            view_count = EXCLUDED.view_count,
            like_count = EXCLUDED.like_count,
            comment_count = EXCLUDED.comment_count,
            loaded_at = CURRENT_TIMESTAMP;
        """
    )

    # Trigger data quality DAG after the update is complete
    trigger_data_quality = TriggerDagRunOperator(
        task_id="trigger_data_quality",
        trigger_dag_id="data_quality",
        wait_for_completion=True,
        poke_interval=60,  # Check every minute
        execution_timeout=timedelta(hours=1),  # 1 hour timeout
    )

    create_schema >> create_staging_table >> create_core_table >> load_json_to_staging_task >> transfer_staging_to_core >> trigger_data_quality