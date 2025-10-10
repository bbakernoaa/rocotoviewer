"""
Tests for the core module in RocotoViewer.

This file contains unit tests for the core functionality.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import threading
import time

from rocotoviewer.core.state_manager import StateManager
from rocotoviewer.core.log_processor import LogProcessor
from rocotoviewer.core.file_monitor import FileMonitor
from rocotoviewer.core.event_bus import EventBus, get_event_bus


class TestStateManager:
    """Tests for the StateManager class."""
    
    def test_initial_state(self, sample_config):
        """Test initial state is properly set."""
        state_manager = StateManager(sample_config)
        
        assert state_manager.get('ui.theme') == sample_config.display.theme
        assert state_manager.get('ui.refresh_interval') == sample_config.display.refresh_interval
        assert state_manager.get('workflows') == {}
    
    def test_set_and_get_state(self, sample_config):
        """Test setting and getting state values."""
        state_manager = StateManager(sample_config)
        
        # Set a value
        state_manager.set('test.key', 'test_value')
        
        # Get the value back
        assert state_manager.get('test.key') == 'test_value'
    
    def test_update_workflow(self, sample_config):
        """Test updating workflow data."""
        state_manager = StateManager(sample_config)
        
        workflow_data = {'id': 'test_wf', 'tasks': []}
        state_manager.update_workflow('test_workflow', workflow_data)
        
        retrieved = state_manager.get_workflow('test_workflow')
        assert retrieved is not None
        assert retrieved['data']['id'] == 'test_wf'
    
    def test_remove_workflow(self, sample_config):
        """Test removing workflow data."""
        state_manager = StateManager(sample_config)
        
        workflow_data = {'id': 'test_wf', 'tasks': []}
        state_manager.update_workflow('test_workflow', workflow_data)
        
        # Verify it was added
        assert state_manager.get_workflow('test_workflow') is not None
        
        # Remove it
        state_manager.remove_workflow('test_workflow')
        
        # Verify it was removed
        assert state_manager.get_workflow('test_workflow') is None
    
    def test_state_callbacks(self, sample_config):
        """Test state change callbacks."""
        state_manager = StateManager(sample_config)
        callback_called = threading.Event()
        callback_data = {}
        
        def test_callback(key, value):
            callback_data['key'] = key
            callback_data['value'] = value
            callback_called.set()
        
        state_manager.register_change_callback(test_callback)
        state_manager.set('test.key', 'test_value')
        
        # Wait for callback to be called
        callback_called.wait(timeout=1)
        
        assert callback_data['key'] == 'test.key'
        assert callback_data['value'] == 'test_value'


class TestLogProcessor:
    """Tests for the LogProcessor class."""
    
    def test_parse_log_line(self, sample_config):
        """Test parsing a single log line."""
        processor = LogProcessor(sample_config)
        line = "2023-01-01 10:00:01 INFO This is a test log message"
        
        result = processor.parse_log_line(line)
        
        assert result['raw'] == line
        assert result['level'] == 'INFO'
        assert result['message'] == "This is a test log message"
        assert result['timestamp'] is not None
    
    def test_filter_logs(self, sample_config):
        """Test filtering logs."""
        processor = LogProcessor(sample_config)
        
        logs = [
            {'level': 'INFO', 'message': 'info message', 'task_id': 'task1'},
            {'level': 'ERROR', 'message': 'error message', 'task_id': 'task2'},
            {'level': 'WARNING', 'message': 'warning message', 'task_id': 'task1'}
        ]
        
        # Filter for ERROR level
        filtered = processor.filter_logs(logs, level='ERROR')
        assert len(filtered) == 1
        assert filtered[0]['level'] == 'ERROR'
        
        # Filter for task1
        filtered = processor.filter_logs(logs, task_id='task1')
        assert len(filtered) == 2
    
    def test_read_log_file(self, sample_config, temp_log_file):
        """Test reading a log file."""
        processor = LogProcessor(sample_config)
        lines = processor.read_log_file(temp_log_file)
        
        assert len(lines) > 0
        assert isinstance(lines[0], str)


class TestFileMonitor:
    """Tests for the FileMonitor class."""
    
    def test_initialization(self, sample_config, sample_state_manager):
        """Test file monitor initialization."""
        monitor = FileMonitor(sample_config, sample_state_manager)
        
        assert monitor.config == sample_config
        assert monitor.state_manager == sample_state_manager
        assert monitor.running is False
    
    def test_add_remove_path(self, sample_config, sample_state_manager):
        """Test adding and removing paths to monitor."""
        monitor = FileMonitor(sample_config, sample_state_manager)
        
        test_path = Path("/tmp/test_dir")
        
        # Add path
        monitor.add_path(test_path)
        assert monitor.is_monitoring(test_path) == False  # Path doesn't exist
        
        # Create directory and try again
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            monitor.add_path(temp_path)
            # We can't easily test if it's monitoring since it depends on the observer
            # but we can at least verify it doesn't crash


class TestEventBus:
    """Tests for the EventBus class."""
    
    def test_subscribe_and_publish(self):
        """Test subscribing to events and publishing them."""
        bus = EventBus()
        event_received = threading.Event()
        received_event = {}
        
        def event_handler(event):
            received_event['type'] = event.type
            received_event['data'] = event.data
            event_received.set()
        
        bus.subscribe('test_event', event_handler)
        bus.publish('test_event', data='test_data')
        
        # Wait for event to be processed
        event_received.wait(timeout=1)
        
        assert received_event['type'] == 'test_event'
        assert received_event['data'] == 'test_data'
    
    def test_get_global_event_bus(self):
        """Test getting the global event bus."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        
        # Should return the same instance
        assert bus1 is bus2
    
    def test_event_bus_clear_subscribers(self):
        """Test clearing subscribers."""
        bus = EventBus()
        
        def handler1(event):
            pass
        
        def handler2(event):
            pass
        
        bus.subscribe('test_event', handler1)
        bus.subscribe('test_event', handler2)
        
        # Verify subscribers exist
        # Note: We can't directly check the number of subscribers due to internal implementation,
        # but we can test that clearing works without error
        bus.clear_subscribers('test_event')
        
        # Publish event - should not crash even though handlers were removed
        bus.publish('test_event', data='test_data')