from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import time
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# YouTube API Key
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Constants
MAX_RESULTS = 100
OUTPUT_DIR = 'data/json'
OUTPUT_FILE = 'youtube_data.json'

def create_youtube_client():
    """Create and return a YouTube API client"""
    try:
        if not YOUTUBE_API_KEY:
            raise ValueError("YOUTUBE_API_KEY environment variable is required")
        return build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
    except Exception as e:
        logger.error(f"Failed to create YouTube client: {str(e)}")
        raise Exception("Could not initialize YouTube API client")

# Alias for test compatibility
def get_youtube_client():
    """Alias for create_youtube_client for test compatibility"""
    return create_youtube_client()

def get_playlist_id(channel_name: str) -> str:
    """
    Get the uploads playlist ID for a YouTube channel by channel name.
    Args:
        channel_name (str): Name of the YouTube channel
    Returns:
        str: Playlist ID of the channel's uploads
    """
    try:
        if not channel_name:
            raise ValueError("Channel name cannot be empty")

        youtube = create_youtube_client()
        
        # Search for the channel
        search_response = youtube.search().list(
            q=channel_name,
            type='channel',
            part='id',
            maxResults=1
        ).execute()
        
        if not search_response.get('items'):
            raise ValueError(f"No channel found with name: {channel_name}")
            
        channel_id = search_response['items'][0]['id']['channelId']
        
        # Get the channel's contentDetails to find uploads playlist
        channel_response = youtube.channels().list(
            id=channel_id,
            part='contentDetails'
        ).execute()
        
        if not channel_response.get('items'):
            raise ValueError(f"Could not get channel details for: {channel_name}")
        
        uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        logger.info(f"Found playlist ID for channel {channel_name}: {uploads_playlist_id}")
        return uploads_playlist_id
        
    except HttpError as e:
        logger.error(f"YouTube API error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error getting playlist ID: {str(e)}")
        raise

def get_video_ids(playlist_id: str) -> Tuple[List[str], int]:
    """
    Get video IDs from a playlist
    Args:
        playlist_id (str): YouTube playlist ID
    Returns:
        Tuple[List[str], int]: List of video IDs and count
    """
    try:
        if not playlist_id:
            raise ValueError("Playlist ID cannot be empty")
        
        youtube = create_youtube_client()
        video_ids = []
        next_page_token = None
        
        while len(video_ids) < MAX_RESULTS:
            try:
                playlist_items = youtube.playlistItems().list(
                    part="contentDetails",
                    playlistId=playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                ).execute()
                
                # Add new video IDs
                new_videos = [
                    item['contentDetails']['videoId'] 
                    for item in playlist_items.get('items', [])
                ]
                video_ids.extend(new_videos)
                
                # Check if we've reached the limit
                if len(video_ids) >= MAX_RESULTS:
                    video_ids = video_ids[:MAX_RESULTS]
                    break
                
                next_page_token = playlist_items.get('nextPageToken')
                if not next_page_token:
                    break
                
                time.sleep(1)  # Rate limiting
                
            except HttpError as e:
                logger.error(f"Error fetching playlist items: {str(e)}")
                break
        
        count = len(video_ids)
        logger.info(f"Retrieved {count} videos from playlist")
        return video_ids, count
        
    except Exception as e:
        logger.error(f"Error getting video IDs: {str(e)}")
        raise

def format_duration(duration: str) -> str:
    """
    Convert YouTube duration format (PT1H2M10S) to readable format (1:02:10)
    Args:
        duration (str): Duration in YouTube format (e.g., 'PT1H2M10S')
    Returns:
        str: Human-readable duration format
    """
    if not duration:
        return "0:00"
        
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return "0:00"
    
    hours, minutes, seconds = match.groups()
    hours = int(hours) if hours else 0
    minutes = int(minutes) if minutes else 0
    seconds = int(seconds) if seconds else 0
    
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"

def extract_video_data(video_ids: List[str]) -> List[Dict]:
    """
    Extract detailed information for a list of video IDs
    Args:
        video_ids (List[str]): List of YouTube video IDs
    Returns:
        List[Dict]: List of video information dictionaries
    """
    if not video_ids:
        logger.warning("No video IDs provided for extraction")
        return []
        
    youtube = create_youtube_client()
    video_data = []
    
    # Process videos in batches of 50 (API limit)
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        try:
            # Get video details for batch
            response = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=','.join(batch)
            ).execute()
            
            # Process each video in the batch
            for video in response.get('items', []):
                try:
                    duration = video['contentDetails']['duration']
                    video_info = {
                        'id': video['id'],  # Match DB expectations
                        'title': video['snippet']['title'],
                        'duration': duration,
                        'video_id': video['id'],
                        'likes': video['statistics'].get('likeCount', '0'),  # Match DB expectations
                        'like_count': video['statistics'].get('likeCount', '0'),
                        'views': video['statistics'].get('viewCount', '0'),  # Match DB expectations  
                        'view_count': video['statistics'].get('viewCount', '0'),
                        'published_at': video['snippet']['publishedAt'],
                        'comments': video['statistics'].get('commentCount', '0'),  # Match DB expectations
                        'comment_count': video['statistics'].get('commentCount', '0'),
                        'duration_readable': format_duration(duration),
                        'snippet': video['snippet'],  # Include full snippet for tests
                        'statistics': video['statistics']  # Include full statistics for tests
                    }
                    video_data.append(video_info)
                except KeyError as e:
                    logger.warning(f"Missing data for video {video['id']}: {str(e)}")
                    continue
                except Exception as e:
                    logger.error(f"Error processing video {video['id']}: {str(e)}")
                    continue
                    
            time.sleep(1)  # Rate limiting between batches
            
        except HttpError as e:
            logger.error(f"YouTube API error in batch {i//50 + 1}: {str(e)}")
            continue
        except Exception as e:
            logger.error(f"Error processing batch {i//50 + 1}: {str(e)}")
            continue
    
    return video_data

# Alias for test compatibility
def get_video_details(youtube_client, video_ids: List[str]) -> List[Dict]:
    """
    Alias for extract_video_data for test compatibility
    Args:
        youtube_client: YouTube API client (ignored, using global client)
        video_ids (List[str]): List of YouTube video IDs
    Returns:
        List[Dict]: List of video information dictionaries
    """
    return extract_video_data(video_ids)

def save_json(channel_handle: str, extracted_data: list):
    """
    Save the extracted data to a JSON file in the data/json directory
    Args:
        channel_handle (str): YouTube channel handle
        extracted_data (list): List of video data dictionaries
    """
    try:
        # Prepare output path
        file_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Prepare the full data structure
        data = {
            "channel_handle": channel_handle,
            "extraction_date": datetime.now().isoformat(),
            "total_videos": len(extracted_data),
            "videos": extracted_data
        }
        
        # Save the data
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        # Verify file
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            logger.info(f"Data saved to {file_path} (Size: {file_size} bytes)")
            logger.info(f"Saved {len(extracted_data)} videos")
        else:
            raise IOError("Failed to create output file")
    except Exception as e:
        logger.error(f"Error saving data to JSON: {str(e)}")
        raise

def main():
    """Main execution function"""
    try:
        # Set channel name to MrBeast
        channel_handle = "MrBeast"
        
        # Get playlist ID
        playlist_id = get_playlist_id(channel_handle)
        if not playlist_id:
            logger.error("Failed to get playlist ID")
            return
        logger.info(f"Using playlist ID: {playlist_id}")
        
        # Get video IDs
        logger.info(f"Fetching video IDs (limited to {MAX_RESULTS} most recent videos)...")
        video_ids, count = get_video_ids(playlist_id)
        
        if not video_ids:
            logger.error("No videos found")
            return
            
        # Extract video data
        logger.info(f"Found {count} videos. Extracting data...")
        video_data = extract_video_data(video_ids)
        
        if not video_data:
            logger.error("No video data extracted")
            return
        
        # Save results
        logger.info("Saving data to JSON file...")
        save_json(channel_handle, video_data)
        logger.info("Data extraction complete")
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        sys.exit(1)

def load_environment():
    """Load and validate environment variables"""
    required_vars = [
        'YOUTUBE_API_KEY'
    ]
    optional_vars = [
        'AIRFLOW_VAR_DATA_PATH', 'AIRFLOW_VAR_JSON_PATH',
        'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_USER', 'POSTGRES_PASSWORD', 'POSTGRES_DB'
    ]
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    if missing:
        logger.error(f"Missing required environment variables: {missing}")
        raise EnvironmentError(f"Required environment variables not set: {missing}")
    
    # Log optional variables that are missing but don't fail
    missing_optional = [var for var in optional_vars if not os.getenv(var)]
    if missing_optional:
        logger.warning(f"Missing optional environment variables: {missing_optional}")
    
    logger.info("Environment variables validated successfully")

def cleanup_old_files(path: str, days: int):
    """Clean up files older than specified days in the given path"""
    import glob
    from datetime import datetime, timedelta

    cutoff = datetime.now() - timedelta(days=days)
    pattern = os.path.join(path, "*.json")
    files = glob.glob(pattern)
    deleted = 0
    for file in files:
        if os.path.getmtime(file) < cutoff.timestamp():
            os.remove(file)
            deleted += 1
            logger.info(f"Deleted old file: {file}")
    logger.info(f"Cleanup complete: {deleted} files deleted")

if __name__ == "__main__":
    main()
