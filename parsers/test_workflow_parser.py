"""
Tests for the refactored WorkflowParser.
"""
import unittest
from pathlib import Path
from .workflow_parser import WorkflowParser
from core.models import Workflow, Task

class TestWorkflowParser(unittest.TestCase):
    """
    Test suite for the refactored WorkflowParser.
    """

    def setUp(self):
        """
        Set up the test case.
        """
        self.parser = WorkflowParser()
        self.sample_workflow_path = str(
            Path(__file__).parent.parent / "examples" / "example_workflow.xml"
        )

    def test_parse_sample_workflow(self):
        """
        Test parsing a sample workflow XML file with the refactored parser.
        """
        workflow = self.parser.parse(self.sample_workflow_path)

        # Assert that a Workflow object is returned
        self.assertIsNotNone(workflow)
        self.assertIsInstance(workflow, Workflow)

        # Assert workflow attributes
        self.assertEqual(workflow.id, "sample_workflow")
        self.assertEqual(workflow.name, "Sample Workflow")
        self.assertIn("This is a sample Rocoto workflow", workflow.description)
        self.assertEqual(workflow.source_file, self.sample_workflow_path)

        # Assert tasks
        self.assertEqual(len(workflow.tasks), 4)
        self.assertIsInstance(workflow.tasks[0], Task)

        # Assertions for the first task (with expanded details)
        task1 = workflow.tasks[0]
        self.assertEqual(task1.id, "task1")
        self.assertEqual(task1.command, "/path/to/script1.sh")
        self.assertEqual(len(task1.dependencies), 1)
        self.assertEqual(task1.dependencies[0].type, 'dependency')
        self.assertEqual(len(task1.envars), 1)
        self.assertEqual(task1.envars[0].name, 'TASK_ID')
        self.assertEqual(task1.envars[0].value, 'task1')

        # Assertions for the newly added nested tags
        self.assertEqual(task1.attributes.get('status'), 'QUEUED')
        self.assertEqual(task1.attributes.get('walltime'), '00:10:00')
        self.assertEqual(task1.attributes.get('queue'), 'debug')

if __name__ == "__main__":
    unittest.main()
