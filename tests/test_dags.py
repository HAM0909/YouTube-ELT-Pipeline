import unittest
from datetime import datetime
from airflow.models import DagBag

class TestDags(unittest.TestCase):
    """Test Airflow DAGs"""
    
    def setUp(self):
        self.dagbag = DagBag(
            dag_folder='dags',
            include_examples=False
        )

    def test_dag_loading(self):
        """Test that all DAGs are loaded correctly"""
        self.assertFalse(
            len(self.dagbag.import_errors),
            f"DAG import errors: {self.dagbag.import_errors}"
        )
        
        expected_dags = {'youtube_elt', 'update_db', 'data_quality'}
        self.assertEqual(
            expected_dags,
            set(self.dagbag.dag_ids),
            "Missing or unexpected DAGs"
        )

    def test_youtube_elt_dag_structure(self):
        """Test the structure of the YouTube ELT DAG"""
        dag = self.dagbag.get_dag('youtube_elt')
        self.assertIsNotNone(dag)
        self.assertEqual(len(dag.tasks), 6)
        
        # Check task order
        start = dag.get_task('start')
        validate_env = dag.get_task('validate_env')
        fetch_videos = dag.get_task('fetch_videos')
        data_quality = dag.get_task('data_quality')
        cleanup = dag.get_task('cleanup')
        end = dag.get_task('end')
        
        # Verify task dependencies
        self.assertIn(validate_env.task_id, [t.task_id for t in start.downstream_list])
        self.assertIn(fetch_videos.task_id, [t.task_id for t in validate_env.downstream_list])
        self.assertIn(data_quality.task_id, [t.task_id for t in fetch_videos.downstream_list])
        self.assertIn(cleanup.task_id, [t.task_id for t in data_quality.downstream_list])
        self.assertIn(end.task_id, [t.task_id for t in cleanup.downstream_list])

    def test_update_db_dag_structure(self):
        """Test the structure of the database update DAG"""
        dag = self.dagbag.get_dag('update_db')
        self.assertIsNotNone(dag)
        
        # Check essential tasks
        required_tasks = {'start', 'create_schema', 'create_staging_table', 'load_staging', 'end'}
        dag_tasks = {task.task_id for task in dag.tasks}
        self.assertTrue(required_tasks.issubset(dag_tasks))
        
        # Verify task dependencies
        load_staging = dag.get_task('load_staging')
        create_table = dag.get_task('create_staging_table')
        self.assertIn(load_staging.task_id, [t.task_id for t in create_table.downstream_list])

    def test_data_quality_dag_structure(self):
        """Test the structure of the data quality DAG"""
        dag = self.dagbag.get_dag('data_quality')
        self.assertIsNotNone(dag)
        
        # Check essential tasks
        required_tasks = {'start', 'run_soda_scan', 'end'}
        dag_tasks = {task.task_id for task in dag.tasks}
        self.assertTrue(required_tasks.issubset(dag_tasks))

    def test_dag_schedules(self):
        """Test that DAGs have correct schedules"""
        dags = {
            'youtube_elt': '0 0 * * *',      # Daily at midnight
            'update_db': '5 0 * * *',        # Daily at 00:05
            'data_quality': '10 0 * * *'     # Daily at 00:10
        }
        
        for dag_id, expected_schedule in dags.items():
            dag = self.dagbag.get_dag(dag_id)
            self.assertEqual(
                dag.schedule_interval,
                expected_schedule,
                f"Incorrect schedule for DAG {dag_id}"
            )

    def test_dag_default_args(self):
        """Test default arguments for all DAGs"""
        for dag_id in self.dagbag.dag_ids:
            dag = self.dagbag.get_dag(dag_id)
            self.assertIsNotNone(dag.default_args)
            self.assertIn('owner', dag.default_args)
            self.assertIn('retries', dag.default_args)
            self.assertIn('retry_delay', dag.default_args)

if __name__ == '__main__':
    unittest.main()