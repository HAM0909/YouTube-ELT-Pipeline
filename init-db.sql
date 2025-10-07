-- Initialize databases and users for the YouTube ELT Pipeline

-- Create the youtube_data database
CREATE DATABASE youtube_data;

-- Switch to youtube_data database and create schemas
\c youtube_data;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS core;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA staging TO airflow;
GRANT ALL PRIVILEGES ON SCHEMA core TO airflow;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA staging TO airflow;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA core TO airflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA staging TO airflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA core TO airflow;

-- Create staging table
CREATE TABLE IF NOT EXISTS staging.videos (
    video_id VARCHAR(50) PRIMARY KEY,
    title TEXT NOT NULL,
    published_at TIMESTAMP NOT NULL,
    duration VARCHAR(20) NOT NULL,
    view_count BIGINT DEFAULT 0,
    like_count BIGINT DEFAULT 0,
    comment_count BIGINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create core table with additional analytics columns
CREATE TABLE IF NOT EXISTS core.videos (
    video_id VARCHAR(50) PRIMARY KEY,
    title TEXT NOT NULL,
    published_at TIMESTAMP NOT NULL,
    duration VARCHAR(20) NOT NULL,
    view_count BIGINT DEFAULT 0,
    like_count BIGINT DEFAULT 0,
    comment_count BIGINT DEFAULT 0,
    engagement_rate DECIMAL(5,4), -- Calculated field
    days_since_published INTEGER, -- Calculated field
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create trigger function for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers
DROP TRIGGER IF EXISTS update_staging_videos_updated_at ON staging.videos;
CREATE TRIGGER update_staging_videos_updated_at
    BEFORE UPDATE ON staging.videos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_core_videos_updated_at ON core.videos;
CREATE TRIGGER update_core_videos_updated_at
    BEFORE UPDATE ON core.videos
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions on the new tables
GRANT ALL PRIVILEGES ON staging.videos TO airflow;
GRANT ALL PRIVILEGES ON core.videos TO airflow;