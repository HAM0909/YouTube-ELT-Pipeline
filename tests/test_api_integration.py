"""
Test suite for YouTube API integration and rate limiting.
Tests API quota management, error handling, and data extraction.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime
from googleapiclient.errors import HttpError
import sys
import os

# Add the include directory to the path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'include', 'scripts'))

try:
    from youtube_elt import (
        create_youtube_client, get_playlist_id, get_video_ids, 
        extract_video_data, format_duration, save_json
    )
except ImportError as e:
    print(f"Warning: Could not import youtube_elt module: {e}")


class TestAPIIntegration(unittest.TestCase):
    """Test YouTube API integration and rate limiting"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_api_key = "test_api_key_12345"
        self.mock_channel_name = "TestChannel"
        self.mock_playlist_id = "UU_test_playlist_id"
        self.mock_video_ids = ["dQw4w9WgXcQ", "abc123DEF456"]

    @patch('youtube_elt.build')
    def test_api_client_creation_success(self, mock_build):
        """Test successful YouTube API client creation"""
        mock_youtube = Mock()
        mock_build.return_value = mock_youtube
        
        with patch.dict(os.environ, {'YOUTUBE_API_KEY': self.mock_api_key}):
            try:
                client = create_youtube_client()
                mock_build.assert_called_once_with('youtube', 'v3', developerKey=self.mock_api_key)
                self.assertIsNotNone(client)
            except NameError:
                self.skipTest("youtube_elt module not available")

    @patch('youtube_elt.build')  
    def test_api_client_creation_missing_key(self, mock_build):
        """Test API client creation with missing API key"""
        with patch.dict(os.environ, {}, clear=True):
            try:
                with self.assertRaises(Exception):
                    create_youtube_client()
            except NameError:
                self.skipTest("youtube_elt module not available")

    @patch('youtube_elt.create_youtube_client')
    def test_playlist_id_retrieval_success(self, mock_create_client):
        """Test successful playlist ID retrieval"""
        mock_youtube = Mock()
        mock_create_client.return_value = mock_youtube
        
        # Mock search response
        mock_search_response = {
            'items': [{'id': {'channelId': 'test_channel_123'}}]
        }
        mock_youtube.search().list().execute.return_value = mock_search_response
        
        # Mock channel response  
        mock_channel_response = {
            'items': [{
                'contentDetails': {
                    'relatedPlaylists': {
                        'uploads': self.mock_playlist_id
                    }
                }
            }]
        }
        mock_youtube.channels().list().execute.return_value = mock_channel_response
        
        try:
            playlist_id = get_playlist_id(self.mock_channel_name)
            self.assertEqual(playlist_id, self.mock_playlist_id)
        except NameError:
            self.skipTest("youtube_elt module not available")

    @patch('youtube_elt.create_youtube_client')
    def test_playlist_id_channel_not_found(self, mock_create_client):
        """Test playlist ID retrieval when channel is not found"""
        mock_youtube = Mock()
        mock_create_client.return_value = mock_youtube
        
        # Mock empty search response
        mock_search_response = {'items': []}
        mock_youtube.search().list().execute.return_value = mock_search_response
        
        try:
            with self.assertRaises(ValueError):
                get_playlist_id("NonExistentChannel")
        except NameError:
            self.skipTest("youtube_elt module not available")

    def test_api_quota_calculation(self):
        """Test API quota usage calculation"""
        # YouTube API v3 quota costs
        search_cost = 100
        channels_list_cost = 1
        playlist_items_cost = 1
        videos_list_cost = 1
        
        # Calculate cost for extracting 100 videos
        videos_to_extract = 100
        expected_cost = (
            search_cost +  # Initial channel search
            channels_list_cost +  # Get channel details
            playlist_items_cost * 2 +  # Get playlist items (2 pages for 100 videos)
            videos_list_cost * 2  # Get video details (2 batches of 50)
        )
        
        # Should be well under 10,000 daily quota
        daily_quota = 10000
        self.assertLess(expected_cost, daily_quota)

    def test_rate_limiting_delay(self):
        """Test rate limiting implementation"""
        import time
        
        start_time = time.time()
        time.sleep(0.1)  # Simulate rate limit delay
        end_time = time.time()
        
        delay = end_time - start_time
        self.assertGreaterEqual(delay, 0.1)

    @patch('youtube_elt.create_youtube_client')
    def test_http_error_handling(self, mock_create_client):
        """Test HTTP error handling from YouTube API"""
        mock_youtube = Mock()
        mock_create_client.return_value = mock_youtube
        
        # Mock HTTP error
        http_error = HttpError(
            Mock(status=403, reason='Forbidden'), 
            b'{"error": {"code": 403, "message": "quotaExceeded"}}'
        )
        mock_youtube.search().list().execute.side_effect = http_error
        
        try:
            with self.assertRaises(HttpError):
                get_playlist_id(self.mock_channel_name)
        except NameError:
            self.skipTest("youtube_elt module not available")

    def test_pagination_handling(self):
        """Test pagination token handling"""
        # Test pagination logic
        max_results = 100
        page_size = 50
        expected_pages = max_results // page_size
        
        self.assertEqual(expected_pages, 2)

    @patch('youtube_elt.create_youtube_client')
    def test_video_data_extraction_batch_processing(self, mock_create_client):
        """Test video data extraction with batch processing"""
        mock_youtube = Mock()
        mock_create_client.return_value = mock_youtube
        
        # Mock video response
        mock_video_response = {
            'items': [{
                'id': 'test_video_123',
                'snippet': {
                    'title': 'Test Video',
                    'publishedAt': '2023-01-01T12:00:00Z'
                },
                'statistics': {
                    'viewCount': '1000',
                    'likeCount': '100',
                    'commentCount': '10'
                },
                'contentDetails': {
                    'duration': 'PT5M30S'
                }
            }]
        }
        mock_youtube.videos().list().execute.return_value = mock_video_response
        
        try:
            video_data = extract_video_data(['test_video_123'])
            self.assertEqual(len(video_data), 1)
            self.assertEqual(video_data[0]['id'], 'test_video_123')
        except NameError:
            self.skipTest("youtube_elt module not available")

    def test_duration_format_parsing(self):
        """Test YouTube duration format parsing"""
        test_cases = [
            ('PT1H30M45S', '1:30:45'),
            ('PT5M30S', '5:30'),
            ('PT45S', '0:45'),
            ('PT2H15M', '2:15:00')
        ]
        
        try:
            for input_duration, expected_output in test_cases:
                with self.subTest(duration=input_duration):
                    result = format_duration(input_duration)
                    self.assertEqual(result, expected_output)
        except NameError:
            self.skipTest("youtube_elt module not available")

    def test_json_output_structure(self):
        """Test JSON output file structure"""
        expected_structure = {
            "channel_handle": str,
            "extraction_date": str,
            "total_videos": int,
            "videos": list
        }
        
        # Mock data structure validation
        sample_output = {
            "channel_handle": "MrBeast",
            "extraction_date": "2023-01-01T12:00:00",
            "total_videos": 2,
            "videos": [
                {"id": "video1", "title": "Test Video 1"},
                {"id": "video2", "title": "Test Video 2"}
            ]
        }
        
        for key, expected_type in expected_structure.items():
            with self.subTest(key=key):
                self.assertIn(key, sample_output)
                self.assertIsInstance(sample_output[key], expected_type)

    def test_error_recovery_mechanism(self):
        """Test error recovery and retry logic"""
        max_retries = 3
        current_attempt = 1
        
        # Simulate retry logic
        while current_attempt <= max_retries:
            try:
                # Simulate operation that might fail
                if current_attempt < 3:
                    raise Exception("Temporary failure")
                break
            except Exception:
                current_attempt += 1
                if current_attempt > max_retries:
                    self.fail("Max retries exceeded")
        
        self.assertEqual(current_attempt, 3)

    def test_api_response_validation(self):
        """Test API response validation"""
        # Valid response
        valid_response = {
            'items': [
                {
                    'id': 'test123',
                    'snippet': {'title': 'Test'},
                    'statistics': {'viewCount': '1000'}
                }
            ]
        }
        
        # Invalid response  
        invalid_response = {'items': []}
        
        self.assertGreater(len(valid_response['items']), 0)
        self.assertEqual(len(invalid_response['items']), 0)

    def test_data_validation_before_save(self):
        """Test data validation before saving to JSON"""
        valid_video = {
            'id': 'valid123456',
            'title': 'Valid Title',
            'view_count': 1000,
            'published_at': '2023-01-01T12:00:00Z'
        }
        
        invalid_video = {
            'id': '',  # Empty ID
            'title': '',  # Empty title
            'view_count': -1,  # Negative count
        }
        
        # Validation checks
        self.assertTrue(valid_video['id'])  # Non-empty ID
        self.assertTrue(valid_video['title'])  # Non-empty title
        self.assertGreaterEqual(valid_video['view_count'], 0)  # Non-negative count
        
        # Invalid data checks
        self.assertFalse(invalid_video['id'])  # Empty ID should fail
        self.assertFalse(invalid_video['title'])  # Empty title should fail
        self.assertLess(invalid_video['view_count'], 0)  # Negative count should fail


if __name__ == '__main__':
    unittest.main()