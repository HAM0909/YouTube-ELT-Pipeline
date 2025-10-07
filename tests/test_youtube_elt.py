import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import unittest
from unittest.mock import patch, MagicMock
from googleapiclient.errors import HttpError
from include.scripts.youtube_elt import get_youtube_client, get_video_details, main, cleanup_old_files, create_youtube_client, extract_video_data

class TestYoutubeELT(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.env_vars = {
            'YOUTUBE_API_KEY': 'test_api_key',
            'YOUTUBE_PLAYLIST_ID': 'test_playlist',
            'AIRFLOW_VAR_JSON_PATH': 'data/json',
            'DATA_RETENTION_DAYS': '7',
            'GOOGLE_API_USE_CLIENT_CERTIFICATE': 'false'
        }
        self.patcher = patch.dict('os.environ', self.env_vars)
        self.patcher.start()
        
        # Create test directory if it doesn't exist
        if not os.path.exists('data/json'):
            os.makedirs('data/json', exist_ok=True)

    def tearDown(self):
        """Clean up test environment"""
        self.patcher.stop()
        # Clean up test files
        try:
            for f in Path('data/json').glob('*.json'):
                f.unlink()
        except Exception:
            pass

    @patch('include.scripts.youtube_elt.build')
    @patch('include.scripts.youtube_elt.YOUTUBE_API_KEY', 'test_api_key')
    def test_get_youtube_client(self, mock_build):
        """Test YouTube client initialization"""
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        
        client = get_youtube_client()
        
        self.assertEqual(client, mock_client)
        mock_build.assert_called_once_with('youtube', 'v3', developerKey='test_api_key')

    @patch('include.scripts.youtube_elt.create_youtube_client')
    def test_get_video_details(self, mock_create_client):
        """Test video details retrieval"""
        mock_youtube = MagicMock()
        mock_create_client.return_value = mock_youtube
        mock_response = {
            'items': [
                {
                    'id': 'video1',
                    'snippet': {'title': 'Test Video', 'publishedAt': '2023-01-01T00:00:00Z'},
                    'statistics': {'viewCount': '1000', 'likeCount': '100', 'commentCount': '10'},
                    'contentDetails': {'duration': 'PT10M30S'}
                }
            ]
        }
        mock_youtube.videos().list().execute.return_value = mock_response
        
        video_ids = ['video1']
        result = get_video_details(mock_youtube, video_ids)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 'video1')
        self.assertEqual(result[0]['snippet']['title'], 'Test Video')

    @patch('include.scripts.youtube_elt.create_youtube_client')
    def test_get_video_details_error_handling(self, mock_create_client):
        """Test video details retrieval error handling"""
        mock_youtube = MagicMock()
        mock_create_client.return_value = mock_youtube
        
        # Mock HTTP error
        http_error = HttpError(
            resp=MagicMock(status=429),
            content=b'Too Many Requests'
        )
        
        mock_youtube.videos().list().execute.side_effect = http_error
        
        video_ids = ['video1']
        result = get_video_details(mock_youtube, video_ids)
        
        # Should return empty list on error
        self.assertEqual(len(result), 0)

    def test_cleanup_old_files(self):
        """Test file cleanup functionality"""
        # Clean up any existing test files first
        try:
            for f in Path('data/json').glob('mrbeast_videos_*.json'):
                f.unlink()
        except Exception:
            pass
            
        # Create test files
        current_date = datetime.now()
        
        # Create files with different dates
        test_files = [
            (current_date - timedelta(days=10), "old_file"),
            (current_date - timedelta(days=3), "recent_file"),
            (current_date, "new_file")
        ]
        
        for date, name in test_files:
            filename = f"mrbeast_videos_{date.strftime('%Y%m%d')}_120000.json"
            filepath = os.path.join('data/json', filename)
            with open(filepath, 'w') as f:
                json.dump({'test': 'data'}, f)
            # Set file modification time
            timestamp = date.timestamp()
            os.utime(filepath, (timestamp, timestamp))
        
        # Run cleanup (7 days retention)
        cleanup_old_files('data/json', 7)
        
        # Check results
        remaining_files = list(Path('data/json').glob('mrbeast_videos_*.json'))
        self.assertEqual(len(remaining_files), 2)  # Should keep recent and new files

    @patch('include.scripts.youtube_elt.create_youtube_client')
    @patch('include.scripts.youtube_elt.get_playlist_id')
    @patch('include.scripts.youtube_elt.get_video_ids')
    @patch('include.scripts.youtube_elt.extract_video_data')
    @patch('include.scripts.youtube_elt.save_json')
    def test_main_successful_execution(self, mock_save_json, mock_extract_video_data, mock_get_video_ids, mock_get_playlist_id, mock_create_client):
        """Test successful execution of the main function"""
        mock_youtube = MagicMock()
        mock_create_client.return_value = mock_youtube
        mock_get_playlist_id.return_value = 'playlist_123'
        mock_get_video_ids.return_value = (['video1', 'video2'], 2)
        mock_extract_video_data.return_value = [
            {'id': 'video1', 'title': 'Test 1'},
            {'id': 'video2', 'title': 'Test 2'}
        ]
        
        main()
        
        # Verify all functions were called correctly
        mock_get_playlist_id.assert_called_once_with('MrBeast')
        mock_get_video_ids.assert_called_once_with('playlist_123')
        mock_extract_video_data.assert_called_once_with(['video1', 'video2'])
        mock_save_json.assert_called_once()

if __name__ == '__main__':
    unittest.main()