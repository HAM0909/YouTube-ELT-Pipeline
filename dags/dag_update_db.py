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
            duration_seconds INTEGER,
            view_count BIGINT,
            like_count BIGINT,
            comment_count BIGINT,
            loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            content_category TEXT,
            performance_score DECIMAL(5,2),
            engagement_rate DECIMAL(5,2),
            is_trending BOOLEAN DEFAULT FALSE,
            video_length_category TEXT,
            like_ratio DECIMAL(5,4)
        );
        
        -- Create indexes for better query performance
        CREATE INDEX IF NOT EXISTS idx_videos_published_at ON core.videos(published_at);
        CREATE INDEX IF NOT EXISTS idx_videos_view_count ON core.videos(view_count);
        CREATE INDEX IF NOT EXISTS idx_videos_category ON core.videos(content_category);
        CREATE INDEX IF NOT EXISTS idx_videos_trending ON core.videos(is_trending);
        """
    )

    load_json_to_staging_task = PythonOperator(
        task_id="load_json_to_staging",
        python_callable=load_json_to_staging,
    )

    transform_and_load_core = PostgresOperator(
        task_id="transform_and_load_core",
        postgres_conn_id="postgres_default",
        sql="""
        INSERT INTO core.videos (
            video_id, title, published_at, duration, duration_seconds,
            view_count, like_count, comment_count,
            content_category, performance_score, engagement_rate,
            is_trending, video_length_category, like_ratio
        )
        SELECT 
            s.video_id,
            s.title,
            s.published_at,
            s.duration,
            -- Convert ISO 8601 duration to seconds
            CASE 
                WHEN s.duration ~ 'PT([0-9]+H)?([0-9]+M)?([0-9]+S)?' THEN
                    COALESCE(REGEXP_REPLACE(s.duration, '.*?([0-9]+)H.*', '\1')::INTEGER * 3600, 0) +
                    COALESCE(REGEXP_REPLACE(s.duration, '.*?([0-9]+)M.*', '\1')::INTEGER * 60, 0) +
                    COALESCE(REGEXP_REPLACE(s.duration, '.*?([0-9]+)S.*', '\1')::INTEGER, 0)
                ELSE 0
            END AS duration_seconds,
            s.view_count,
            s.like_count,
            s.comment_count,
            -- Content categorization based on title keywords
            CASE 
                WHEN UPPER(s.title) LIKE '%CHALLENGE%' OR UPPER(s.title) LIKE '%VS%' THEN 'Challenge'
                WHEN UPPER(s.title) LIKE '%REACT%' OR UPPER(s.title) LIKE '%REACTION%' THEN 'Reaction'
                WHEN UPPER(s.title) LIKE '%GAMING%' OR UPPER(s.title) LIKE '%PLAYS%' THEN 'Gaming'
                WHEN UPPER(s.title) LIKE '%COOKING%' OR UPPER(s.title) LIKE '%RECIPE%' THEN 'Cooking'
                WHEN UPPER(s.title) LIKE '%TRAVEL%' OR UPPER(s.title) LIKE '%VISIT%' THEN 'Travel'
                WHEN UPPER(s.title) LIKE '%MONEY%' OR UPPER(s.title) LIKE '%DOLLAR%' OR UPPER(s.title) LIKE '$' THEN 'Money/Business'
                WHEN UPPER(s.title) LIKE '%GIVING%' OR UPPER(s.title) LIKE '%HELP%' OR UPPER(s.title) LIKE '%CHARITY%' THEN 'Philanthropy'
                ELSE 'Entertainment'
            END AS content_category,
            -- Performance score based on engagement metrics (0-100)
            LEAST(100, 
                (s.like_count::DECIMAL / NULLIF(s.view_count, 0) * 100 * 50) +
                (s.comment_count::DECIMAL / NULLIF(s.view_count, 0) * 100 * 50)
            ) AS performance_score,
            -- Engagement rate calculation  
            ((s.like_count + s.comment_count)::DECIMAL / NULLIF(s.view_count, 0) * 100) AS engagement_rate,
            -- Trending determination (top 10% by recent views)
            CASE 
                WHEN s.view_count >= (
                    SELECT PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY view_count) 
                    FROM staging.videos 
                    WHERE published_at > CURRENT_DATE - INTERVAL '30 days'
                ) THEN TRUE
                ELSE FALSE
            END AS is_trending,
            -- Video length categorization
            CASE 
                WHEN COALESCE(REGEXP_REPLACE(s.duration, '.*?([0-9]+)H.*', '\1')::INTEGER * 3600, 0) +
                     COALESCE(REGEXP_REPLACE(s.duration, '.*?([0-9]+)M.*', '\1')::INTEGER * 60, 0) +
                     COALESCE(REGEXP_REPLACE(s.duration, '.*?([0-9]+)S.*', '\1')::INTEGER, 0) < 60 THEN 'Short (<1min)'
                WHEN COALESCE(REGEXP_REPLACE(s.duration, '.*?([0-9]+)H.*', '\1')::INTEGER * 3600, 0) +
                     COALESCE(REGEXP_REPLACE(s.duration, '.*?([0-9]+)M.*', '\1')::INTEGER * 60, 0) +
                     COALESCE(REGEXP_REPLACE(s.duration, '.*?([0-9]+)S.*', '\1')::INTEGER, 0) < 300 THEN 'Medium (1-5min)'
                WHEN COALESCE(REGEXP_REPLACE(s.duration, '.*?([0-9]+)H.*', '\1')::INTEGER * 3600, 0) +
                     COALESCE(REGEXP_REPLACE(s.duration, '.*?([0-9]+)M.*', '\1')::INTEGER * 60, 0) +
                     COALESCE(REGEXP_REPLACE(s.duration, '.*?([0-9]+)S.*', '\1')::INTEGER, 0) < 1200 THEN 'Long (5-20min)'
                ELSE 'Extended (20min+)'
            END AS video_length_category,
            -- Like ratio calculation
            (s.like_count::DECIMAL / NULLIF(s.view_count, 0)) AS like_ratio
        FROM staging.videos s
        ON CONFLICT (video_id) DO UPDATE SET
            title = EXCLUDED.title,
            published_at = EXCLUDED.published_at,
            duration = EXCLUDED.duration,
            duration_seconds = EXCLUDED.duration_seconds,
            view_count = EXCLUDED.view_count,
            like_count = EXCLUDED.like_count,
            comment_count = EXCLUDED.comment_count,
            content_category = EXCLUDED.content_category,
            performance_score = EXCLUDED.performance_score,
            engagement_rate = EXCLUDED.engagement_rate,
            is_trending = EXCLUDED.is_trending,
            video_length_category = EXCLUDED.video_length_category,
            like_ratio = EXCLUDED.like_ratio,
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

    create_schema >> create_staging_table >> create_core_table >> load_json_to_staging_task >> transform_and_load_core >> trigger_data_quality