"""
Tests for the real-time log tailing functionality.
"""

import tempfile
import time
import threading
from pathlib import Path
import pytest

from ..core.file_monitor import FileMonitor
from ..core.log_processor import LogProcessor
from ..core.state_manager import StateManager
from ..config.config import Config


def test_log_tailing_integration():
    """Test the integration of file monitoring, log processing, and state management."""
    
    # Create a temporary log file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as temp_log:
        temp_log_path = Path(temp_log.name)
        # Write initial content
        temp_log.write("2023-01-01 10:00:00 INFO Starting workflow\n")
        temp_log.flush()
    
    try:
        # Create a basic config
        config = Config()
        config.workflows = [{'path': str(temp_log_path)}]
        config.monitor = type('MonitorConfig', (), {
            'enabled': True,
            'poll_interval': 1,
            'max_file_size': 10485760
        })()
        config.display = type('DisplayConfig', (), {
            'max_log_lines': 1000
        })()
        
        # Create state manager
        state_manager = StateManager(config)
        
        # Create log processor
        log_processor = LogProcessor(config)
        
        # Create file monitor with event bus
        from ..core.event_bus import EventBus
        event_bus = EventBus()
        file_monitor = FileMonitor(config, state_manager, event_bus)
        
        # Track new log entries
        new_entries = []
        
        def log_callback(log_entry):
            new_entries.append(log_entry)
        
        # Register callback for new log entries
        log_processor.register_stream_callback(temp_log_path, log_callback)
        
        # Start monitoring
        file_monitor.start()
        
        # Add more content to the log file to trigger tailing
        with open(temp_log_path, 'a') as f:
            f.write("2023-01-01 10:01:00 INFO Task task1 submitted\n")
            f.write("2023-01-01 10:02:00 INFO Task task1 succeeded\n")
            f.flush()
        
        # Wait for the monitoring to process the new content
        time.sleep(0.5)
        
        # Check that new entries were captured
        assert len(new_entries) >= 2, f"Expected at least 2 new entries, got {len(new_entries)}"
        
        # Verify the content of the entries
        task_submitted_found = any("submitted" in entry.get('message', '') for entry in new_entries)
        task_succeeded_found = any("succeeded" in entry.get('message', '') for entry in new_entries)
        
        assert task_submitted_found, "Task submitted entry not found"
        assert task_succeeded_found, "Task succeeded entry not found"
        
        # Test processing of a new line directly
        new_line = "2023-01-01 10:03:00 ERROR Task task2 failed"
        processed_entry = log_processor.process_new_log_line(temp_log_path, new_line)
        
        assert processed_entry is not None
        assert processed_entry['level'] == 'ERROR'
        assert 'task2' in processed_entry['message']
        
        # Stop monitoring
        file_monitor.stop()
        
    finally:
        # Clean up the temporary file
        if temp_log_path.exists():
            temp_log_path.unlink()


def test_large_file_handling():
    """Test handling of large files with the enhanced file utilities."""
    
    from ..utils.file_utils import FileUtils
    
    # Create a temporary large file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as temp_log:
        temp_log_path = Path(temp_log.name)
        # Write a large number of lines
        for i in range(5000):  # 5000 lines
            temp_log.write(f"2023-01-01 10:{i%60:02d}:{i%60:02d} INFO Log message {i}\n")
        temp_log.flush()
    
    try:
        # Test reading the tail of the large file
        tail_lines = FileUtils.read_large_file_tail(temp_log_path, num_lines=100)
        
        assert len(tail_lines) == 100, f"Expected 100 lines, got {len(tail_lines)}"
        
        # Verify the last line is correct
        last_line = tail_lines[-1]
        assert "Log message 4999" in last_line, f"Expected last line to contain 'Log message 499', got: {last_line}"
        
        # Test the tail generator
        gen_lines = list(FileUtils.tail_file_generator(temp_log_path, max_lines=50))
        assert len(gen_lines) == 50, f"Expected 50 lines from generator, got {len(gen_lines)}"
        
    finally:
        # Clean up the temporary file
        if temp_log_path.exists():
            temp_log_path.unlink()


def test_streaming_log_processor():
    """Test the streaming log processor functionality."""
    
    # Create a basic config
    config = Config()
    config.workflows = []
    config.display = type('DisplayConfig', (), {
        'max_log_lines': 100
    })()
    
    # Create streaming log processor
    log_processor = LogProcessor(config)
    
    # Test registering and unregistering callbacks
    test_path = Path("/tmp/test.log")
    callback_called = []
    
    def test_callback(entry):
        callback_called.append(entry)
    
    log_processor.register_stream_callback(test_path, test_callback)
    
    # Process a new log line
    test_line = "2023-01-01 12:00 INFO Test message"
    result = log_processor.process_new_log_line(test_path, test_line)
    
    assert result is not None
    assert len(callback_called) == 1
    assert callback_called[0]['message'] == 'Test message'
    
    # Test unregistering callback
    log_processor.unregister_stream_callback(test_path, test_callback)
    
    # Process another line - callback should not be called
    prev_count = len(callback_called)
    result2 = log_processor.process_new_log_line(test_path, "2023-01-01 12:01:00 INFO Another message")
    
    # The callback shouldn't have been called again since it was unregistered
    # However, the entry should still be in the buffer
    streaming_logs = log_processor.get_streaming_logs(test_path, count=10)
    assert len(streaming_logs) >= 1  # Should have at least the first entry


if __name__ == "__main__":
    test_log_tailing_integration()
    test_large_file_handling()
    test_streaming_log_processor()
    print("All tests passed!")