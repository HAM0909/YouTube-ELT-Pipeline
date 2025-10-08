"""
YouTube ELT Pipeline Dashboard
Simple dashboard for visualizing YouTube video analytics
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import psycopg2
import os
from typing import Optional, Dict, Any

# Configuration
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'postgres'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'password')
}

# Page configuration
st.set_page_config(
    page_title="YouTube ELT Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def get_database_connection():
    """Create database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_video_data() -> Optional[pd.DataFrame]:
    """Load video data from PostgreSQL"""
    conn = get_database_connection()
    if not conn:
        return None
    
    try:
        query = """
        SELECT 
            video_id,
            title,
            published_at,
            duration,
            duration_seconds,
            view_count,
            like_count,
            comment_count,
            loaded_at,
            content_category,
            performance_score,
            engagement_rate,
            is_trending,
            video_length_category,
            like_ratio
        FROM core.videos
        ORDER BY published_at DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        conn.close()
        return None

def create_metrics_cards(df: pd.DataFrame):
    """Create key metrics cards"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_videos = len(df)
        st.metric("Total Videos", f"{total_videos:,}")
    
    with col2:
        total_views = df['view_count'].sum()
        st.metric("Total Views", f"{total_views:,.0f}")
    
    with col3:
        avg_engagement = df['engagement_rate'].mean()
        st.metric("Avg Engagement Rate", f"{avg_engagement:.2f}%")
    
    with col4:
        trending_count = df['is_trending'].sum()
        st.metric("Trending Videos", f"{trending_count}")

def create_views_timeline(df: pd.DataFrame):
    """Create views over time chart"""
    st.subheader("📈 Views Timeline")
    
    # Prepare data
    df_timeline = df.copy()
    df_timeline['published_date'] = pd.to_datetime(df_timeline['published_at']).dt.date
    
    # Aggregate by date
    timeline_data = df_timeline.groupby('published_date').agg({
        'view_count': 'sum',
        'like_count': 'sum',
        'comment_count': 'sum'
    }).reset_index()
    
    # Create chart
    fig = px.line(
        timeline_data, 
        x='published_date', 
        y='view_count',
        title='Total Views by Publication Date',
        labels={'view_count': 'Views', 'published_date': 'Date'}
    )
    fig.update_traces(line_color='#FF6B6B')
    
    st.plotly_chart(fig, use_container_width=True)

def create_category_analysis(df: pd.DataFrame):
    """Create content category analysis"""
    st.subheader("🎯 Content Category Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Category distribution
        category_counts = df['content_category'].value_counts()
        
        fig_pie = px.pie(
            values=category_counts.values,
            names=category_counts.index,
            title="Video Distribution by Category"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Category performance
        category_performance = df.groupby('content_category').agg({
            'view_count': 'mean',
            'engagement_rate': 'mean',
            'performance_score': 'mean'
        }).reset_index()
        
        fig_bar = px.bar(
            category_performance,
            x='content_category',
            y='view_count',
            title="Average Views by Category",
            labels={'view_count': 'Average Views', 'content_category': 'Category'}
        )
        fig_bar.update_traces(marker_color='#4ECDC4')
        st.plotly_chart(fig_bar, use_container_width=True)

def create_performance_scatter(df: pd.DataFrame):
    """Create performance scatter plot"""
    st.subheader("🎪 Performance Analysis")
    
    fig = px.scatter(
        df,
        x='view_count',
        y='engagement_rate',
        size='like_count',
        color='content_category',
        hover_data=['title', 'performance_score'],
        title='Views vs Engagement Rate (sized by likes)',
        labels={
            'view_count': 'Views',
            'engagement_rate': 'Engagement Rate (%)',
            'content_category': 'Category'
        }
    )
    
    st.plotly_chart(fig, use_container_width=True)

def create_top_videos_table(df: pd.DataFrame):
    """Create top performing videos table"""
    st.subheader("🏆 Top Performing Videos")
    
    # Select and format top videos
    top_videos = df.nlargest(10, 'view_count')[
        ['title', 'view_count', 'like_count', 'comment_count', 'engagement_rate', 'content_category']
    ].copy()
    
    # Format numbers
    top_videos['view_count'] = top_videos['view_count'].apply(lambda x: f"{x:,.0f}")
    top_videos['like_count'] = top_videos['like_count'].apply(lambda x: f"{x:,.0f}")
    top_videos['comment_count'] = top_videos['comment_count'].apply(lambda x: f"{x:,.0f}")
    top_videos['engagement_rate'] = top_videos['engagement_rate'].apply(lambda x: f"{x:.2f}%")
    
    # Rename columns
    top_videos.columns = ['Title', 'Views', 'Likes', 'Comments', 'Engagement %', 'Category']
    
    st.dataframe(top_videos, use_container_width=True)

def create_video_length_analysis(df: pd.DataFrame):
    """Analyze video length performance"""
    st.subheader("⏱️ Video Length Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Length category distribution
        length_counts = df['video_length_category'].value_counts()
        
        fig_pie = px.pie(
            values=length_counts.values,
            names=length_counts.index,
            title="Video Distribution by Length"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Length vs performance
        length_performance = df.groupby('video_length_category').agg({
            'view_count': 'mean',
            'engagement_rate': 'mean'
        }).reset_index()
        
        fig_bar = px.bar(
            length_performance,
            x='video_length_category',
            y='engagement_rate',
            title="Average Engagement by Video Length",
            labels={'engagement_rate': 'Engagement Rate (%)', 'video_length_category': 'Length Category'}
        )
        fig_bar.update_traces(marker_color='#95E1D3')
        st.plotly_chart(fig_bar, use_container_width=True)

def create_trending_analysis(df: pd.DataFrame):
    """Analyze trending videos"""
    st.subheader("🔥 Trending Videos Analysis")
    
    trending_df = df[df['is_trending'] == True]
    
    if len(trending_df) > 0:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_views = trending_df['view_count'].mean()
            st.metric("Avg Views (Trending)", f"{avg_views:,.0f}")
        
        with col2:
            avg_engagement = trending_df['engagement_rate'].mean()
            st.metric("Avg Engagement (Trending)", f"{avg_engagement:.2f}%")
        
        with col3:
            trending_categories = trending_df['content_category'].mode().iloc[0] if len(trending_df) > 0 else "N/A"
            st.metric("Most Trending Category", trending_categories)
        
        # Trending videos table
        st.write("**Current Trending Videos:**")
        trending_display = trending_df[['title', 'view_count', 'engagement_rate', 'content_category']].copy()
        trending_display['view_count'] = trending_display['view_count'].apply(lambda x: f"{x:,.0f}")
        trending_display['engagement_rate'] = trending_display['engagement_rate'].apply(lambda x: f"{x:.2f}%")
        trending_display.columns = ['Title', 'Views', 'Engagement %', 'Category']
        
        st.dataframe(trending_display, use_container_width=True)
    else:
        st.info("No videos currently marked as trending")

def create_data_quality_status():
    """Show data quality status"""
    st.subheader("✅ Data Quality Status")
    
    conn = get_database_connection()
    if not conn:
        st.error("Cannot check data quality - database connection failed")
        return
    
    try:
        # Check data freshness
        freshness_query = """
        SELECT 
            MAX(loaded_at) as last_update,
            COUNT(*) as total_records,
            COUNT(CASE WHEN view_count < 0 THEN 1 END) as negative_views,
            COUNT(CASE WHEN like_count < 0 THEN 1 END) as negative_likes,
            COUNT(CASE WHEN LENGTH(video_id) != 11 THEN 1 END) as invalid_ids
        FROM core.videos
        """
        
        quality_df = pd.read_sql_query(freshness_query, conn)
        conn.close()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            last_update = quality_df['last_update'].iloc[0]
            if last_update:
                hours_ago = (datetime.now() - pd.to_datetime(last_update)).total_seconds() / 3600
                st.metric("Data Freshness", f"{hours_ago:.1f} hours ago")
            else:
                st.metric("Data Freshness", "No data")
        
        with col2:
            total_records = quality_df['total_records'].iloc[0]
            st.metric("Total Records", f"{total_records:,}")
        
        with col3:
            data_issues = (quality_df['negative_views'].iloc[0] + 
                          quality_df['negative_likes'].iloc[0] + 
                          quality_df['invalid_ids'].iloc[0])
            status = "✅ Good" if data_issues == 0 else f"⚠️ {data_issues} issues"
            st.metric("Data Quality", status)
        
        with col4:
            if total_records > 0:
                completeness = 100 - (data_issues / total_records * 100)
                st.metric("Completeness", f"{completeness:.1f}%")
            else:
                st.metric("Completeness", "0%")
        
    except Exception as e:
        st.error(f"Error checking data quality: {e}")
        conn.close()

def main():
    """Main dashboard application"""
    # Header
    st.title("📊 YouTube ELT Pipeline Dashboard")
    st.markdown("**Analyzing MrBeast Channel Performance**")
    
    # Sidebar
    st.sidebar.title("Dashboard Controls")
    
    # Auto-refresh option
    auto_refresh = st.sidebar.checkbox("Auto-refresh (30s)", value=False)
    if auto_refresh:
        st.sidebar.info("Dashboard will refresh every 30 seconds")
        st.rerun()
    
    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    # Load data
    with st.spinner("Loading video data..."):
        df = load_video_data()
    
    if df is None or len(df) == 0:
        st.error("No data available. Please check your database connection and ensure the pipeline has run.")
        st.info("Make sure the PostgreSQL database is running and contains data in the core.videos table.")
        return
    
    st.success(f"✅ Loaded {len(df)} videos successfully")
    
    # Date filter
    if not df.empty:
        min_date = pd.to_datetime(df['published_at']).min().date()
        max_date = pd.to_datetime(df['published_at']).max().date()
        
        date_range = st.sidebar.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
        
        if len(date_range) == 2:
            start_date, end_date = date_range
            df = df[
                (pd.to_datetime(df['published_at']).dt.date >= start_date) &
                (pd.to_datetime(df['published_at']).dt.date <= end_date)
            ]
    
    # Category filter
    categories = df['content_category'].unique()
    selected_categories = st.sidebar.multiselect(
        "Content Categories",
        categories,
        default=categories
    )
    
    if selected_categories:
        df = df[df['content_category'].isin(selected_categories)]
    
    # Main dashboard content
    create_metrics_cards(df)
    
    st.divider()
    
    # Charts and analysis
    create_views_timeline(df)
    create_category_analysis(df)
    create_performance_scatter(df)
    create_video_length_analysis(df)
    create_trending_analysis(df)
    create_top_videos_table(df)
    
    st.divider()
    
    # Data quality status
    create_data_quality_status()
    
    # Footer
    st.markdown("---")
    st.markdown("**YouTube ELT Pipeline Dashboard** | Last updated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    main()