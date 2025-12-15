"""
File monitoring module for RocotoViewer.

This module monitors workflow files for changes and notifies the application
when updates occur, with enhanced real-time tailing capabilities for log files.
"""

import time
import threading
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from collections import defaultdict
from utils.file_utils import FileUtils


class WorkflowFileHandler(FileSystemEventHandler):
    """
    Event handler for workflow file changes.
    """
    
    def __init__(self, callback: Callable[[str, str], None]):
        """
        Initialize the file handler.
        
        Args:
            callback: Function to call when file changes occur
        """
        super().__init__()
        self.callback = callback
        self.logger = logging.getLogger(__name__)
    
    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory:
            self._handle_event('modified', str(event.src_path))

    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self._handle_event('created', str(event.src_path))

    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory:
            self._handle_event('deleted', str(event.src_path))

    def on_moved(self, event):
        """Handle file move events."""
        if not event.is_directory:
            dest_path = getattr(event, 'dest_path', event.src_path)
            self._handle_event('moved', str(dest_path))
    
    def _handle_event(self, event_type: str, file_path: str):
        """
        Handle a file system event.
        
        Args:
            event_type: Type of event (modified, created, deleted, moved)
            file_path: Path to the file that changed
        """
        try:
            self.callback(event_type, file_path)
        except Exception as e:
            self.logger.error(f"Error in file event callback: {str(e)}")


class FileMonitor:
    """
    Monitors workflow files and directories for changes with real-time log tailing capabilities.
    """
    
    def __init__(self, config, state_manager, event_bus=None, log_processor=None):
        """
        Initialize the file monitor.
        
        Args:
            config: Application configuration
            state_manager: State manager instance
            event_bus: Optional event bus for notifications
            log_processor: Optional log processor for integrating log processing
        """
        self.config = config
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.log_processor = log_processor
        self.logger = logging.getLogger(__name__)
        
        self.observer = Observer()
        self.monitoring_paths = set()
        self.log_tailing_paths: Dict[Path, int] = {}  # Path -> last_read_position
        self.event_handler = WorkflowFileHandler(self._on_file_change)
        self.running = False
        self.thread = None
        
        # Set up monitoring based on configuration
        self._setup_monitoring()
    
    def _setup_monitoring(self):
        """Set up monitoring based on configuration."""
        for workflow_config in self.config.workflows:
            path = Path(workflow_config['path'])
            if path.exists():
                if path.is_file():
                    self.monitoring_paths.add(path.parent)
                else:
                    self.monitoring_paths.add(path)
    
    def _on_file_change(self, event_type: str, file_path: str):
        """
        Handle file change events.
        
        Args:
            event_type: Type of file system event
            file_path: Path to the changed file
        """
        self.logger.info(f"File {event_type}: {file_path}")
        
        # Notify state manager about the change
        self.state_manager.update_from_file_change(event_type, file_path)
        
        # Optionally trigger UI updates or other actions
        self._trigger_refresh(event_type, file_path)

    def _is_log_file(self, file_path: Path) -> bool:
        """Check if the file is a log file based on extension or name pattern."""
        return (file_path.suffix.lower() in ['.log', '.out', '.err'] or
                'log' in file_path.name.lower())
    
    
    def _process_new_log_line(self, file_path: Path, line: str):
        """Process a new log line from tailing."""
        try:
            if self.log_processor:
                # Use the log processor to handle the new line
                self.log_processor.process_new_log_line(file_path, line)
            else:
                # Fallback to old behavior if no log processor is provided
                self.state_manager.add_log_entry('default', {
                    'timestamp': time.time(),
                    'file_path': str(file_path),
                    'line': line,
                    'source': 'tail'
                })

            # Emit event via event bus if available
            if self.event_bus:
                self.event_bus.publish('log_line_added', {
                    'file_path': str(file_path),
                    'line': line,
                    'timestamp': time.time()
                })

        except Exception as e:
            self.logger.error(f"Error processing new log line from {file_path}: {str(e)}")
    
    def _trigger_refresh(self, event_type: str, file_path: str):
        """
        Trigger refresh operations based on file changes.
        
        Args:
            event_type: Type of file system event
            file_path: Path to the changed file
        """
        # In a real implementation, this might trigger UI updates,
        # re-parsing of workflows, etc.
        pass
    
    def start(self):
        """Start monitoring files."""
        if self.running:
            self.logger.warning("File monitor already running")
            return
        
        # Schedule all monitoring paths
        for path in self.monitoring_paths:
            if path.exists():
                self.observer.schedule(self.event_handler, str(path), recursive=True)
                self.logger.info(f"Monitoring path: {path}")
        
        self.observer.start()
        self.running = True
        
        # Start monitoring thread if needed
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        
        self.logger.info("File monitoring started")

    def _monitor_loop(self):
        """Main monitoring loop for polling log files."""
        while self.running:
            for path, last_pos in list(self.log_tailing_paths.items()):
                if not path.exists():
                    continue
                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        f.seek(last_pos)
                        new_lines = f.readlines()
                        if new_lines:
                            for line in new_lines:
                                self._process_new_log_line(path, line.strip())
                            self.log_tailing_paths[path] = f.tell()
                except Exception as e:
                    self.logger.error(f"Error tailing file {path}: {e}")
            time.sleep(self.config.monitor.poll_interval)
    
    def stop(self):
        """Stop monitoring files."""
        if not self.running:
            return
        
        self.observer.stop()
        self.observer.join(timeout=5)  # Wait up to 5 seconds for cleanup
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        
        self.logger.info("File monitoring stopped")
    
    def add_path(self, path: Path):
        """
        Add a path to monitor.
        
        Args:
            path: Path to add to monitoring
        """
        if not path.exists():
            self.logger.warning(f"Path does not exist, cannot monitor: {path}")
            return
        
        if path not in self.monitoring_paths:
            self.monitoring_paths.add(path)
            
            if self.running:
                # Add to observer if already running
                self.observer.schedule(self.event_handler, str(path), recursive=True)
                self.logger.info(f"Added monitoring path: {path}")
    
    def remove_path(self, path: Path):
        """
        Remove a path from monitoring.
        
        Args:
            path: Path to remove from monitoring
        """
        if path in self.monitoring_paths:
            self.monitoring_paths.remove(path)
            self.logger.info(f"Removed monitoring path: {path}")
    
    def is_monitoring(self, path: Path) -> bool:
        """
        Check if a path is being monitored.
        
        Args:
            path: Path to check
            
        Returns:
            True if path is being monitored, False otherwise
        """
        return path in self.monitoring_paths
    
    def add_log_file_for_tailing(self, file_path: Path):
        """
        Add a log file to be tailed in real-time.
        
        Args:
            file_path: Path to the log file to tail
        """
        if not file_path.exists():
            self.logger.warning(f"Log file does not exist, cannot tail: {file_path}")
            return
        
        if file_path not in self.log_tailing_paths:
            self.log_tailing_paths[file_path] = file_path.stat().st_size if file_path.exists() else 0
            self.logger.info(f"Added log file for tailing: {file_path}")
    
    def remove_log_file_from_tailing(self, file_path: Path):
        """
        Remove a log file from real-time tailing.
        
        Args:
            file_path: Path to the log file to stop tailing
        """
        if file_path in self.log_tailing_paths:
            del self.log_tailing_paths[file_path]
            self.logger.info(f"Removed log file from tailing: {file_path}")
    
    def is_tailing(self, file_path: Path) -> bool:
        """
        Check if a log file is being tailed.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if log file is being tailed, False otherwise
        """
        return file_path in self.log_tailing_paths