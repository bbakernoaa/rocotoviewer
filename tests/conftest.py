"""
Pytest configuration for RocotoViewer tests.

This file contains fixtures and configuration for the test suite.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, MagicMock

from rocotoviewer.config.config import Config
from rocotoviewer.core.state_manager import StateManager
from rocotoviewer.core.log_processor import LogProcessor
from rocotoviewer.parsers.workflow_parser import WorkflowParser


@pytest.fixture
def sample_config():
    """Create a sample configuration for testing."""
    config = Config()
    config.display.refresh_interval = 1  # Faster for tests
    config.monitor.poll_interval = 1     # Faster for tests
    return config


@pytest.fixture
def sample_state_manager(sample_config):
    """Create a sample state manager for testing."""
    return StateManager(sample_config)


@pytest.fixture
def sample_log_processor(sample_config):
    """Create a sample log processor for testing."""
    return LogProcessor(sample_config)


@pytest.fixture
def sample_workflow_parser(sample_config):
    """Create a sample workflow parser for testing."""
    return WorkflowParser(sample_config)


@pytest.fixture
def temp_workflow_file():
    """Create a temporary workflow file for testing."""
    content = '''<?xml version="1.0" encoding="UTF-8"?>
<workflow workflowid="test_workflow" name="Test Workflow">
  <tasks>
    <task name="test_task1">
      <command>/bin/echo "test"</command>
    </task>
    <task name="test_task2">
      <command>/bin/echo "test2"</command>
      <dependency>
        <taskdep task="test_task1" />
      </dependency>
    </task>
  </tasks>
</workflow>'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def temp_log_file():
    """Create a temporary log file for testing."""
    content = '''2023-01-01 10:00:01 INFO Workflow started successfully
2023-01-01 10:05:23 INFO Task test_task1 submitted to queue
2023-01-01 10:10:45 ERROR Task test_task2 failed with exit code 1
2023-01-01 10:15:12 WARNING Resource usage high for task test_task3
2023-01-01 10:20:33 INFO Task test_task4 completed successfully'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        f.write(content)
        temp_path = Path(f.name)
    
    yield temp_path
    
    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def mock_file_monitor():
    """Create a mock file monitor for testing."""
    mock = Mock()
    mock.start = Mock()
    mock.stop = Mock()
    mock.is_monitoring = Mock(return_value=True)
    return mock


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus for testing."""
    mock = Mock()
    mock.subscribe = Mock()
    mock.publish = Mock()
    mock.unsubscribe = Mock()
    return mock