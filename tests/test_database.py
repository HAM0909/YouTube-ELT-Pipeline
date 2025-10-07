import unittest
from unittest.mock import patch, MagicMock
import json
import os
from datetime import datetime

class TestDatabaseOperations(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        self.env_vars = {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass'
        }
        self.patcher = patch.dict('os.environ', self.env_vars)
        self.patcher.start()

    def tearDown(self):
        """Clean up test environment"""
        self.patcher.stop()

    @patch('airflow.providers.postgres.hooks.postgres.PostgresHook')
    def test_load_json_to_staging(self, mock_pg_hook):
        """Test JSON data loading to staging table"""
        from dags.update_db import load_json_to_staging
        
        # Mock database connection and cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pg_hook.return_value.get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Create test JSON data
        test_data = [{
            'id': 'test_video_1',
            'snippet': {
                'title': 'Test Video',
                'publishedAt': '2023-09-18T00:00:00Z'
            },
            'contentDetails': {
                'duration': 'PT10M'
            },
            'statistics': {
                'viewCount': '1000',
                'likeCount': '100',
                'commentCount': '10'
            }
        }]
        
        # Create test JSON file
        test_dir = '/tmp/test_json'
        os.makedirs(test_dir, exist_ok=True)
        test_file = f"{test_dir}/mrbeast_videos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        
        # Run the function
        with patch.dict('os.environ', {'AIRFLOW_VAR_JSON_PATH': test_dir}):
            load_json_to_staging()
        
        # Verify the SQL execution
        mock_cursor.execute.assert_called()
        args = mock_cursor.execute.call_args[0]
        self.assertIn('INSERT INTO staging.videos', args[0])
        
        # Clean up
        os.remove(test_file)
        os.rmdir(test_dir)

    @patch('airflow.providers.postgres.hooks.postgres.PostgresHook')
    def test_create_staging_table(self, mock_pg_hook):
        """Test staging table creation"""
        from dags.update_db import create_staging_table
        
        # Mock database connection
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pg_hook.return_value.get_conn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Execute the operator
        task = create_staging_table
        task.execute(context={})
        
        # Verify SQL execution
        mock_cursor.execute.assert_called()
        args = mock_cursor.execute.call_args[0]
        self.assertIn('CREATE TABLE IF NOT EXISTS staging.videos', args[0])

if __name__ == '__main__':
    unittest.main()