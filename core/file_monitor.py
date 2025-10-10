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
from ..utils.file_utils import FileUtils


class LogFileTailer:
    """
    Tail log files in real-time, similar to 'tail -f'.
    """
    
    def __init__(self, file_path: Path, callback: Callable[[str], None], 
                 buffer_size: int = 4096, max_buffer_lines: int = 1000):
        """
        Initialize the log file tailer.
        
        Args:
            file_path: Path to the log file to tail
            callback: Function to call when new lines are available
            buffer_size: Size of buffer to read at a time
            max_buffer_lines: Maximum lines to keep in buffer
        """
        self.file_path = file_path
        self.callback = callback
        self.buffer_size = buffer_size
        self.max_buffer_lines = max_buffer_lines
        self.logger = logging.getLogger(__name__)
        
        # Track file position
        self.position = 0
        self.file_handle = None
        self.running = False
        self.thread = None
        
        # Track file rotation
        self.inode = None
        self.size = 0
        
    def start(self):
        """Start tailing the log file."""
        if self.running:
            return
            
        # Get initial file position
        if self.file_path.exists():
            try:
                self.file_handle = open(self.file_path, 'r', encoding='utf-8', errors='ignore')
                # Go to end of file
                self.file_handle.seek(0, os.SEEK_END)
                self.position = self.file_handle.tell()
                self.inode = os.stat(self.file_path).st_ino
                self.size = os.stat(self.file_path).st_size
            except Exception as e:
                self.logger.error(f"Error opening file {self.file_path}: {str(e)}")
                return
        
        self.running = True
        self.thread = threading.Thread(target=self._tail_loop, daemon=True)
        self.thread.start()
        
        self.logger.info(f"Started tailing log file: {self.file_path}")
    
    def stop(self):
        """Stop tailing the log file."""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
        
        if self.file_handle:
            self.file_handle.close()
            self.file_handle = None
            
        self.logger.info(f"Stopped tailing log file: {self.file_path}")
    
    def _tail_loop(self):
        """Main tailing loop."""
        while self.running:
            try:
                self._check_for_updates()
                time.sleep(0.1)  # Small delay to prevent busy waiting
            except Exception as e:
                self.logger.error(f"Error in tail loop for {self.file_path}: {str(e)}")
                time.sleep(1)  # Brief pause before retrying
    
    def _check_for_updates(self):
        """Check for new content in the log file."""
        if not self.file_path.exists():
            # File doesn't exist, check if it was rotated
            if self.file_handle:
                self.file_handle.close()
                self.file_handle = None
            return
        
        try:
            # Check if file was rotated (different inode or smaller size)
            current_inode = os.stat(self.file_path).st_ino
            current_size = os.stat(self.file_path).st_size
            
            # Handle file rotation
            if (self.inode is not None and 
                (current_inode != self.inode or current_size < self.size)):
                self.logger.info(f"File rotation detected for {self.file_path}")
                if self.file_handle:
                    self.file_handle.close()
                self.file_handle = open(self.file_path, 'r', encoding='utf-8', errors='ignore')
                self.position = 0  # Start from beginning of new file
                self.inode = current_inode
                self.size = current_size
            
            # Check if file handle is None and try to open
            if self.file_handle is None:
                self.file_handle = open(self.file_path, 'r', encoding='utf-8', errors='ignore')
                self.file_handle.seek(0, os.SEEK_END)
                self.position = self.file_handle.tell()
                self.inode = os.stat(self.file_path).st_ino
                self.size = current_size
            
            # Get current file size
            current_pos = self.file_handle.tell()
            file_size = os.path.getsize(self.file_path)
            
            # Check if file has grown
            if file_size > current_pos:
                # Read new content
                self.file_handle.seek(current_pos)
                new_content = self.file_handle.read(file_size - current_pos)
                
                if new_content:
                    # Split into lines and send each line to callback
                    lines = new_content.split('\n')
                    
                    # Handle the case where the last line doesn't end with newline
                    if new_content.endswith('\n'):
                        # Process all lines
                        for line in lines[:-1]:  # Exclude the last empty string
                            if line.strip():
                                self.callback(line)
                    else:
                        # Last line is incomplete, keep it for next read
                        for line in lines[:-1]:  # Process complete lines
                            if line.strip():
                                self.callback(line)
                        # The incomplete line is in lines[-1], we'll handle it next time
                        
                self.position = self.file_handle.tell()
                self.size = file_size
                
        except Exception as e:
            self.logger.error(f"Error checking updates for {self.file_path}: {str(e)}")
            # Try to reopen the file handle if there was an error
            try:
                if self.file_handle:
                    self.file_handle.close()
                self.file_handle = open(self.file_path, 'r', encoding='utf-8', errors='ignore')
                self.file_handle.seek(0, os.SEEK_END)
                self.position = self.file_handle.tell()
            except Exception as reopen_error:
                self.logger.error(f"Error reopening file {self.file_path}: {str(reopen_error)}")


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
            self._handle_event('modified', event.src_path)
    
    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory:
            self._handle_event('created', event.src_path)
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory:
            self._handle_event('deleted', event.src_path)
    
    def on_moved(self, event):
        """Handle file move events."""
        if not event.is_directory:
            self._handle_event('moved', event.dest_path if hasattr(event, 'dest_path') else event.src_path)
    
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
    
    def __init__(self, config, state_manager, event_bus=None):
        """
        Initialize the file monitor.
        
        Args:
            config: Application configuration
            state_manager: State manager instance
            event_bus: Optional event bus for notifications
        """
        self.config = config
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        self.observer = Observer()
        self.monitoring_paths = set()
        self.log_tailing_paths = set()
        self.tailers: Dict[Path, LogFileTailer] = {}
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
        
        # Check if this is a log file and handle tailing
        file_path_obj = Path(file_path)
        if self._is_log_file(file_path_obj):
            self._handle_log_file_change(event_type, file_path_obj)
        
        # Optionally trigger UI updates or other actions
        self._trigger_refresh(event_type, file_path)
    
    def _is_log_file(self, file_path: Path) -> bool:
        """Check if the file is a log file based on extension or name pattern."""
        return (file_path.suffix.lower() in ['.log', '.out', '.err'] or 
                'log' in file_path.name.lower())
    
    def _handle_log_file_change(self, event_type: str, file_path: Path):
        """Handle log file changes specifically for real-time tailing."""
        if event_type == 'created' and file_path in self.log_tailing_paths:
            # New log file created, start tailing if not already
            if file_path not in self.tailers:
                self._start_tailing_log_file(file_path)
        elif event_type == 'deleted' and file_path in self.tailers:
            # Log file deleted, stop tailing
            self._stop_tailing_log_file(file_path)
    
    def _start_tailing_log_file(self, file_path: Path):
        """Start tailing a log file."""
        def log_callback(line: str):
            # Process the new log line
            self._process_new_log_line(file_path, line)
        
        tailer = LogFileTailer(file_path, log_callback)
        self.tailers[file_path] = tailer
        tailer.start()
        self.logger.info(f"Started tailing log file: {file_path}")
    
    def _stop_tailing_log_file(self, file_path: Path):
        """Stop tailing a log file."""
        if file_path in self.tailers:
            self.tailers[file_path].stop()
            del self.tailers[file_path]
            self.logger.info(f"Stopped tailing log file: {file_path}")
    
    def _process_new_log_line(self, file_path: Path, line: str):
        """Process a new log line from tailing."""
        try:
            # Add the new log line to the state manager
            self.state_manager.add_log_entry({
                'timestamp': time.time(),
                'file_path': str(file_path),
                'line': line,
                'source': 'tail'
            })
            
            # Emit event via event bus if available
            if self.event_bus:
                self.event_bus.emit('log_line_added', {
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
        
        # Start tailing any existing log files
        self._start_existing_log_tailing()
        
        self.logger.info("File monitoring started")
    
    def _start_existing_log_tailing(self):
        """Start tailing any existing log files that should be tailed."""
        for workflow_config in self.config.workflows:
            path = Path(workflow_config['path'])
            if path.is_file() and self._is_log_file(path):
                self.add_log_file_for_tailing(path)
            elif path.is_dir():
                # Find log files in the directory
                log_files = FileUtils.find_files(path, extensions=['.log', '.out', '.err'])
                for log_file in log_files:
                    self.add_log_file_for_tailing(log_file)
    
    def _monitor_loop(self):
        """Main monitoring loop (if needed for polling approach)."""
        while self.running:
            # Additional monitoring logic can go here if needed
            # For now, we rely on the watchdog observer and log tailers
            time.sleep(1)
    
    def stop(self):
        """Stop monitoring files."""
        if not self.running:
            return
        
        # Stop all log tailers
        for file_path in list(self.tailers.keys()):
            self._stop_tailing_log_file(file_path)
        
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
            self.log_tailing_paths.add(file_path)
            
            if self.running:
                # Start tailing if monitor is already running
                self._start_tailing_log_file(file_path)
    
    def remove_log_file_from_tailing(self, file_path: Path):
        """
        Remove a log file from real-time tailing.
        
        Args:
            file_path: Path to the log file to stop tailing
        """
        if file_path in self.log_tailing_paths:
            self.log_tailing_paths.remove(file_path)
            self._stop_tailing_log_file(file_path)
    
    def is_tailing(self, file_path: Path) -> bool:
        """
        Check if a log file is being tailed.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if log file is being tailed, False otherwise
        """
        return file_path in self.tailers