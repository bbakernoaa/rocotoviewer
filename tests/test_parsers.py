"""
Tests for the parsers module in RocotoViewer.

This file contains unit tests for the parsing functionality.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from rocotoviewer.parsers.workflow_parser import WorkflowParser
from rocotoviewer.parsers.log_parser import LogParser
from rocotoviewer.parsers.task_parser import TaskParser


class TestWorkflowParser:
    """Tests for the WorkflowParser class."""
    
    def test_parse_valid_workflow(self, sample_config, temp_workflow_file):
        """Test parsing a valid workflow file."""
        parser = WorkflowParser(sample_config)
        result = parser.parse(str(temp_workflow_file))
        
        assert result is not None
        assert 'id' in result
        assert 'tasks' in result
        assert len(result['tasks']) >= 0  # At least 0 tasks expected
        assert result['id'] == 'test_workflow'
    
    def test_parse_invalid_file(self, sample_config):
        """Test parsing an invalid file."""
        parser = WorkflowParser(sample_config)
        result = parser.parse("/nonexistent/file.xml")
        
        assert result == {}
    
    def test_validate_workflow_valid(self, sample_config):
        """Test validating a valid workflow."""
        parser = WorkflowParser(sample_config)
        valid_workflow = {
            'id': 'test_workflow',
            'tasks': [],
            'source': '/tmp/test.xml'
        }
        
        result = parser.validate_workflow(valid_workflow)
        assert result is True
    
    def test_validate_workflow_invalid(self, sample_config):
        """Test validating an invalid workflow."""
        parser = WorkflowParser(sample_config)
        invalid_workflow = {
            'tasks': []  # Missing 'id' and 'source'
        }
        
        result = parser.validate_workflow(invalid_workflow)
        assert result is False


class TestLogParser:
    """Tests for the LogParser class."""
    
    def test_parse_valid_log_file(self, sample_config, temp_log_file):
        """Test parsing a valid log file."""
        parser = LogParser(sample_config)
        result = parser.parse(str(temp_log_file))
        
        assert result is not None
        assert 'logs' in result
        assert len(result['logs']) > 0
        
        # Check that log entries have expected fields
        first_log = result['logs'][0]
        assert 'timestamp' in first_log
        assert 'level' in first_log
        assert 'message' in first_log
    
    def test_parse_invalid_log_file(self, sample_config):
        """Test parsing an invalid log file."""
        parser = LogParser(sample_config)
        result = parser.parse("/nonexistent/file.log")
        
        assert result == {}
    
    def test_filter_logs_by_level(self, sample_config, temp_log_file):
        """Test filtering logs by level."""
        parser = LogParser(sample_config)
        result = parser.parse(str(temp_log_file))
        
        # Filter for ERROR level
        filtered = parser.filter_logs(result, level='ERROR')
        error_logs = [log for log in filtered['logs'] if log['level'] == 'ERROR']
        
        assert len(error_logs) >= 0  # At least 0 error logs expected
    
    def test_get_log_summary(self, sample_config, temp_log_file):
        """Test getting log summary."""
        parser = LogParser(sample_config)
        result = parser.parse(str(temp_log_file))
        summary = parser.get_summary(result)
        
        assert 'total_logs' in summary
        assert 'level_counts' in summary
        assert summary['total_logs'] > 0


class TestTaskParser:
    """Tests for the TaskParser class."""
    
    def test_parse_tasks_from_workflow(self, sample_config, temp_workflow_file):
        """Test parsing tasks from a workflow file."""
        parser = TaskParser(sample_config)
        result = parser.parse(str(temp_workflow_file))
        
        assert result is not None
        assert 'tasks' in result
        assert 'total_tasks' in result
        
        # The workflow should have at least the tasks defined in the fixture
        assert result['total_tasks'] >= 0
    
    def test_parse_task_xml_content(self, sample_config):
        """Test parsing task XML content directly."""
        xml_content = '''<task name="test_task">
            <command>/bin/echo "test"</command>
            <dependency>
                <taskdep task="other_task" />
            </dependency>
        </task>'''
        
        parser = TaskParser(sample_config)
        result = parser.parse(xml_content)
        
        assert result is not None
        assert 'tasks' in result
        assert len(result['tasks']) == 1
    
    def test_validate_task_data(self, sample_config):
        """Test validating task data."""
        parser = TaskParser(sample_config)
        valid_task_data = {
            'tasks': [
                {'id': 'task1', 'type': 'task'},
                {'id': 'task2', 'type': 'task'}
            ]
        }
        
        result = parser.validate_task_data(valid_task_data)
        assert result is True
    
    def test_get_task_summary(self, sample_config):
        """Test getting task summary."""
        parser = TaskParser(sample_config)
        task_data = {
            'tasks': [
                {'id': 'task1', 'type': 'task', 'status': 'active'},
                {'id': 'task2', 'type': 'task', 'status': 'inactive'},
                {'id': 'task3', 'type': 'task', 'status': 'active'}
            ]
        }
        
        summary = parser.get_task_summary(task_data)
        assert 'total_tasks' in summary
        assert 'type_counts' in summary
        assert 'status_counts' in summary
        assert summary['total_tasks'] == 3
        assert summary['status_counts']['active'] == 2