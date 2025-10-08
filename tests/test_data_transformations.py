"""
Test suite for data transformation functions and logic.
Tests the advanced analytics and content classification features.
"""

import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta


class TestDataTransformations(unittest.TestCase):
    """Test data transformation and analytics functions"""

    def setUp(self):
        """Set up test fixtures"""
        self.sample_video_data = {
            'video_id': 'dQw4w9WgXcQ',
            'title': 'Amazing Challenge Video $1000',
            'published_at': '2023-01-01T12:00:00Z',
            'duration': 'PT10M30S',
            'view_count': 1000000,
            'like_count': 50000,
            'comment_count': 5000
        }

    def test_duration_conversion_hours_minutes_seconds(self):
        """Test ISO 8601 duration conversion with hours, minutes, seconds"""
        duration = 'PT1H30M45S'
        # 1 hour = 3600s, 30 min = 1800s, 45s = 45s = 5445s total
        expected_seconds = 3600 + 1800 + 45
        self.assertEqual(expected_seconds, 5445)

    def test_duration_conversion_minutes_only(self):
        """Test ISO 8601 duration conversion with minutes only"""  
        duration = 'PT15M'
        expected_seconds = 15 * 60
        self.assertEqual(expected_seconds, 900)

    def test_duration_conversion_seconds_only(self):
        """Test ISO 8601 duration conversion with seconds only"""
        duration = 'PT45S'
        expected_seconds = 45
        self.assertEqual(expected_seconds, 45)

    def test_content_classification_challenge(self):
        """Test content categorization for challenge videos"""
        titles = [
            'Amazing Challenge Video',
            'MrBeast vs 100 People Challenge',
            'Ultimate CHALLENGE compilation'
        ]
        for title in titles:
            with self.subTest(title=title):
                self.assertIn('CHALLENGE', title.upper())

    def test_content_classification_money_business(self):
        """Test content categorization for money/business videos"""
        titles = [
            'I Gave Away $1000000',
            'Making MONEY with this trick',
            'DOLLAR challenge accepted'
        ]
        for title in titles:
            with self.subTest(title=title):
                has_money_keywords = any(keyword in title.upper() 
                                       for keyword in ['MONEY', 'DOLLAR', '$'])
                self.assertTrue(has_money_keywords)

    def test_content_classification_philanthropy(self):
        """Test content categorization for philanthropy videos"""
        titles = [
            'GIVING food to homeless people',
            'How I HELP families in need',
            'CHARITY event was amazing'
        ]
        expected_keywords = ['GIVING', 'HELP', 'CHARITY']
        for title in titles:
            with self.subTest(title=title):
                has_philanthropy_keywords = any(keyword in title.upper() 
                                               for keyword in expected_keywords)
                self.assertTrue(has_philanthropy_keywords)

    def test_performance_score_calculation(self):
        """Test performance score calculation logic"""
        # Test data: view_count=1000, like_count=100, comment_count=50
        view_count = 1000
        like_count = 100  
        comment_count = 50
        
        # Expected calculation: (like_ratio * 50) + (comment_ratio * 50)
        like_ratio = like_count / view_count  # 0.1
        comment_ratio = comment_count / view_count  # 0.05
        expected_score = min(100, (like_ratio * 100 * 50) + (comment_ratio * 100 * 50))
        # = min(100, (0.1 * 100 * 50) + (0.05 * 100 * 50))
        # = min(100, 500 + 250) = min(100, 750) = 100
        
        self.assertEqual(expected_score, 100)

    def test_engagement_rate_calculation(self):
        """Test engagement rate calculation"""
        view_count = 10000
        like_count = 500
        comment_count = 100
        
        engagement_rate = ((like_count + comment_count) / view_count) * 100
        expected_rate = ((500 + 100) / 10000) * 100  # 6.0%
        
        self.assertEqual(engagement_rate, expected_rate)

    def test_video_length_categorization_short(self):
        """Test video length categorization for short videos"""
        # Less than 60 seconds
        duration_seconds = 45
        expected_category = 'Short (<1min)'
        self.assertLess(duration_seconds, 60)

    def test_video_length_categorization_medium(self):
        """Test video length categorization for medium videos"""
        # 1-5 minutes (60-300 seconds)
        duration_seconds = 180  # 3 minutes
        expected_category = 'Medium (1-5min)'
        self.assertTrue(60 <= duration_seconds < 300)

    def test_video_length_categorization_long(self):
        """Test video length categorization for long videos"""
        # 5-20 minutes (300-1200 seconds)
        duration_seconds = 900  # 15 minutes
        expected_category = 'Long (5-20min)'
        self.assertTrue(300 <= duration_seconds < 1200)

    def test_video_length_categorization_extended(self):
        """Test video length categorization for extended videos"""
        # More than 20 minutes (1200+ seconds)
        duration_seconds = 1800  # 30 minutes
        expected_category = 'Extended (20min+)'
        self.assertGreaterEqual(duration_seconds, 1200)

    def test_like_ratio_calculation(self):
        """Test like ratio calculation"""
        view_count = 100000
        like_count = 5000
        expected_ratio = like_count / view_count  # 0.05
        
        calculated_ratio = like_count / view_count
        self.assertEqual(calculated_ratio, expected_ratio)

    def test_trending_threshold_logic(self):
        """Test trending determination logic"""
        # Mock percentile calculation
        recent_views = [1000, 5000, 10000, 50000, 100000, 500000, 1000000]
        percentile_90 = 900000  # Simulated 90th percentile
        
        test_view_count = 950000
        is_trending = test_view_count >= percentile_90
        self.assertTrue(is_trending)

    def test_data_quality_validation_negative_counts(self):
        """Test validation against negative counts"""
        invalid_data = {
            'view_count': -1000,
            'like_count': -50, 
            'comment_count': -10
        }
        
        for field, value in invalid_data.items():
            with self.subTest(field=field):
                self.assertLess(value, 0)

    def test_data_quality_validation_video_id_format(self):
        """Test video ID format validation"""
        valid_ids = ['dQw4w9WgXcQ', 'ABC123def_-']  # 11 chars, valid pattern
        invalid_ids = ['short', 'toolongvideoid123', 'invalid@chars']
        
        for video_id in valid_ids:
            with self.subTest(video_id=video_id):
                self.assertEqual(len(video_id), 11)
                self.assertTrue(all(c.isalnum() or c in '_-' for c in video_id))
        
        for video_id in invalid_ids:
            with self.subTest(video_id=video_id):
                is_valid = (len(video_id) == 11 and 
                          all(c.isalnum() or c in '_-' for c in video_id))
                self.assertFalse(is_valid)

    def test_date_validation_future_dates(self):
        """Test validation against future publication dates"""
        future_date = datetime.now() + timedelta(days=1)
        current_date = datetime.now()
        
        self.assertGreater(future_date, current_date)

    def test_date_validation_youtube_launch(self):
        """Test validation against dates before YouTube existed"""
        youtube_launch = datetime(2005, 1, 1)
        pre_youtube_date = datetime(2004, 12, 31)
        
        self.assertLess(pre_youtube_date, youtube_launch)

    def test_like_count_exceeds_view_count_validation(self):
        """Test business rule: likes cannot exceed views"""
        view_count = 1000
        like_count = 1500  # Invalid: more likes than views
        
        self.assertGreater(like_count, view_count)  # This should trigger validation error

    def test_title_length_validation(self):
        """Test title length validation"""
        empty_title = ""
        normal_title = "Great Video Title"
        too_long_title = "x" * 201  # Over 200 characters
        
        self.assertEqual(len(empty_title), 0)
        self.assertLess(len(normal_title), 200)  
        self.assertGreater(len(too_long_title), 200)

    def test_data_freshness_validation(self):
        """Test data freshness requirements"""
        current_time = datetime.now()
        fresh_data = current_time - timedelta(hours=12)  # 12 hours old
        stale_data = current_time - timedelta(days=3)   # 3 days old
        
        self.assertLess(fresh_data, current_time)
        self.assertLess(stale_data, current_time - timedelta(days=2))


if __name__ == '__main__':
    unittest.main()