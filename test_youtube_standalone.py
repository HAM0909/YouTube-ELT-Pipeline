#!/usr/bin/env python3
"""
Standalone test script for YouTube ELT functionality
This script tests the core YouTube ELT functions without Airflow dependencies
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add the include directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'include', 'scripts'))

class TestYouTubeStandalone(unittest.TestCase):
    """Test YouTube ELT functionality standalone"""
    
    def setUp(self):
        """Set up test environment"""
        self.env_vars = {
            'YOUTUBE_API_KEY': 'test_api_key_here'
        }
        self.patcher = patch.dict('os.environ', self.env_vars)
        self.patcher.start()
    
    def tearDown(self):
        """Clean up test environment"""
        self.patcher.stop()
    
    def test_imports(self):
        """Test that all required functions can be imported"""
        try:
            from youtube_elt import (
                create_youtube_client, get_youtube_client, 
                get_playlist_id, get_video_ids, extract_video_data,
                format_duration, save_json, main, load_environment,
                cleanup_old_files
            )
            self.assertTrue(True, "All imports successful")
        except ImportError as e:
            self.fail(f"Import failed: {e}")
    
    @patch('youtube_elt.build')
    def test_create_youtube_client(self, mock_build):
        """Test YouTube client creation"""
        from youtube_elt import create_youtube_client
        
        mock_client = MagicMock()
        mock_build.return_value = mock_client
        
        client = create_youtube_client()
        
        self.assertEqual(client, mock_client)
        mock_build.assert_called_once_with('youtube', 'v3', developerKey='test_api_key_here')
    
    def test_format_duration(self):
        """Test duration formatting"""
        from youtube_elt import format_duration
        
        # Test various duration formats
        test_cases = [
            ('PT1H2M10S', '1:02:10'),
            ('PT30M15S', '30:15'),
            ('PT5M', '5:00'),
            ('PT45S', '0:45'),
            ('PT2H', '2:00:00'),
            ('', '0:00'),
            ('INVALID', '0:00')
        ]
        
        for input_duration, expected in test_cases:
            with self.subTest(input_duration=input_duration):
                result = format_duration(input_duration)
                self.assertEqual(result, expected)
    
    def test_load_environment_success(self):
        """Test successful environment loading"""
        from youtube_elt import load_environment
        
        # Should not raise exception with API key set
        try:
            load_environment()
        except Exception as e:
            self.fail(f"load_environment raised exception: {e}")
    
    def test_load_environment_missing_api_key(self):
        """Test environment loading with missing API key"""
        from youtube_elt import load_environment
        
        # Remove API key from environment
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(EnvironmentError):
                load_environment()
    
    @patch('youtube_elt.create_youtube_client')
    def test_extract_video_data(self, mock_create_client):
        """Test video data extraction"""
        from youtube_elt import extract_video_data
        
        mock_youtube = MagicMock()
        mock_create_client.return_value = mock_youtube
        
        # Mock response from YouTube API
        mock_response = {
            'items': [
                {
                    'id': 'video1',
                    'snippet': {
                        'title': 'Test Video 1',
                        'publishedAt': '2023-01-01T00:00:00Z'
                    },
                    'statistics': {
                        'viewCount': '1000',
                        'likeCount': '100',
                        'commentCount': '10'
                    },
                    'contentDetails': {
                        'duration': 'PT10M30S'
                    }
                }
            ]
        }
        mock_youtube.videos().list().execute.return_value = mock_response
        
        video_ids = ['video1']
        result = extract_video_data(video_ids)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 'video1')
        self.assertEqual(result[0]['title'], 'Test Video 1')
        self.assertEqual(result[0]['views'], '1000')
        self.assertEqual(result[0]['likes'], '100')
        self.assertEqual(result[0]['comments'], '10')

if __name__ == '__main__':
    # Run the standalone tests
    unittest.main()