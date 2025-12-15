"""
Log processing module for RocotoViewer.

This module handles reading, parsing, and processing workflow logs with streaming support.
"""

import re
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Generator
from datetime import datetime
import logging
from collections import deque
from utils.file_utils import FileUtils
from config.settings import Settings


class LogProcessingError(Exception):
    """Base exception for log processing errors."""
    pass

class LogFileAccessError(LogProcessingError):
    """Raised when a log file cannot be accessed."""
    pass

class LogParseError(LogProcessingError):
    """Raised when a log line cannot be parsed."""
    pass


class StreamingLogProcessor:
    """
    Handles processing of workflow logs with streaming and real-time capabilities.
    """
    
    def __init__(self, config):
        """
        Initialize the streaming log processor with configuration.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Common log patterns for Rocoto workflows
        self.patterns = Settings().LOG_PATTERNS
        
        # Buffer for streaming logs
        self.stream_buffers: Dict[Path, deque] = {}
        self.max_buffer_size = getattr(config, 'max_log_buffer_size', 10000)
        
        # Callbacks for real-time processing
        self.stream_callbacks: Dict[Path, List[Callable]] = {}
    
    def register_stream_callback(self, log_path: Path, callback: Callable[[Dict[str, Any]], None]):
        """
        Register a callback to receive real-time log updates.
        
        Args:
            log_path: Path to the log file
            callback: Function to call when new log entries are available
        """
        if log_path not in self.stream_callbacks:
            self.stream_callbacks[log_path] = []
        
        self.stream_callbacks[log_path].append(callback)
        
        # Initialize buffer for this log file if not already done
        if log_path not in self.stream_buffers:
            self.stream_buffers[log_path] = deque(maxlen=self.max_buffer_size)
    
    def unregister_stream_callback(self, log_path: Path, callback: Callable[[Dict[str, Any]], None]):
        """
        Unregister a callback from receiving real-time log updates.
        
        Args:
            log_path: Path to the log file
            callback: Function to remove from callbacks
        """
        if log_path in self.stream_callbacks:
            if callback in self.stream_callbacks[log_path]:
                self.stream_callbacks[log_path].remove(callback)
    
    def process_new_log_line(self, log_path: Path, line: str) -> Optional[Dict[str, Any]]:
        """
        Process a new log line in real-time.
        
        Args:
            log_path: Path to the log file
            line: New log line to process
            
        Returns:
            Parsed log entry or None if parsing failed
        """
        parsed_entry = self.parse_log_line(line)
        
        if parsed_entry:
            # Add file path and timestamp to the entry
            parsed_entry['file_path'] = str(log_path)
            parsed_entry['received_at'] = time.time()
            
            # Add to buffer
            if log_path not in self.stream_buffers:
                self.stream_buffers[log_path] = deque(maxlen=self.max_buffer_size)
            
            self.stream_buffers[log_path].append(parsed_entry)
            
            # Call registered callbacks
            if log_path in self.stream_callbacks:
                for callback in self.stream_callbacks[log_path]:
                    try:
                        callback(parsed_entry)
                    except Exception as e:
                        self.logger.error(f"Error in stream callback for {log_path}: {str(e)}")
        
        return parsed_entry
    
    def read_log_file_streaming(self, log_path: Path,
                              max_lines: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:
        """
        Read log file in streaming fashion, yielding one entry at a time.
        
        Args:
            log_path: Path to log file
            max_lines: Maximum number of lines to read (from end)
            
        Yields:
            Parsed log entries as dictionaries
        """
        if not log_path.exists():
            self.logger.warning(f"Log file does not exist: {log_path}")
            raise LogFileAccessError(f"Log file does not exist: {log_path}")
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            if max_lines and len(lines) > max_lines:
                # Process last max_lines lines
                lines = lines[-max_lines:]
                
            for line in lines:
                line = line.rstrip('\n\r')
                parsed_entry = self.parse_log_line(line)
                if parsed_entry:
                    parsed_entry['file_path'] = str(log_path)
                    parsed_entry['received_at'] = time.time()
                    yield parsed_entry
                    
        except Exception as e:
            self.logger.error(f"Error reading log file {log_path}: {str(e)}")
            raise LogFileAccessError(f"Failed to read log file {log_path}: {str(e)}")
    
    def read_log_file(self, log_path: Path, max_lines: Optional[int] = None) -> List[str]:
        """
        Read log file with optional line limit.
        
        Args:
            log_path: Path to log file
            max_lines: Maximum number of lines to read (from end)
            
        Returns:
            List of log lines
        """
        if not log_path.exists():
            self.logger.warning(f"Log file does not exist: {log_path}")
            raise LogFileAccessError(f"Log file does not exist: {log_path}")
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
            if max_lines and len(lines) > max_lines:
                # Return last max_lines lines
                lines = lines[-max_lines:]
                
            return [line.rstrip('\n\r') for line in lines]
            
        except Exception as e:
            self.logger.error(f"Error reading log file {log_path}: {str(e)}")
            raise LogFileAccessError(f"Failed to read log file {log_path}: {str(e)}")
    
    def parse_log_line(self, line: str) -> Dict[str, Any]:
        """
        Parse a single log line into structured data.
        
        Args:
            line: Log line to parse
            
        Returns:
            Dictionary with parsed log data
        """
        result = {
            'raw': line,
            'timestamp': None,
            'level': 'INFO',
            'message': line,
            'task_id': None,
            'cycle': None,
            'status': None,
            'source_file': None
        }
        
        # Extract timestamp
        timestamp_match = re.search(self.patterns['timestamp'], line)
        if timestamp_match:
            try:
                result['timestamp'] = datetime.strptime(timestamp_match.group(), '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    # Try alternative timestamp formats
                    result['timestamp'] = datetime.strptime(timestamp_match.group(), '%Y-%m-%d %H:%M:%S.%f')
                except ValueError:
                    pass  # If timestamp format is unexpected, leave as None
        
        # Extract task ID
        task_match = re.search(self.patterns['task_id'], line)
        if not task_match:
            task_match = re.search(self.patterns['rocoto_task'], line)
        if task_match:
            result['task_id'] = task_match.group(1) if len(task_match.groups()) > 0 else task_match.group()
        
        # Extract cycle info
        cycle_match = re.search(self.patterns['cycle_info'], line)
        if cycle_match:
            result['cycle'] = cycle_match.group(1)
        
        # Extract status
        status_match = re.search(self.patterns['task_status'], line, re.IGNORECASE)
        if status_match:
            result['status'] = status_match.group()
        
        # Determine log level
        upper_line = line.upper()
        if 'ERROR' in upper_line:
            result['level'] = 'ERROR'
        elif 'WARN' in upper_line:
            result['level'] = 'WARNING'
        elif 'DEBUG' in upper_line:
            result['level'] = 'DEBUG'
        elif 'INFO' in upper_line:
            result['level'] = 'INFO'
        
        # Extract the main message part
        # Remove timestamp and other structured elements to get the core message
        message = line
        if timestamp_match:
            message = message.replace(timestamp_match.group(), '', 1).strip()
        # Remove log level if it's at the beginning
        if result['level'] in message:
            # Use regex to remove the log level more precisely
            message = re.sub(r'^' + re.escape(result['level']), '', message, count=1).strip()
        result['message'] = message.strip()
        
        return result
    
    def filter_logs(self, logs: List[Dict[str, Any]], 
                   level: Optional[str] = None,
                   task_id: Optional[str] = None,
                   status: Optional[str] = None,
                   search_term: Optional[str] = None,
                   start_time: Optional[float] = None,
                   end_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Filter logs based on various criteria.
        
        Args:
            logs: List of parsed log dictionaries
            level: Log level to filter (INFO, WARNING, ERROR, DEBUG)
            task_id: Task ID to filter
            status: Status to filter (succeeded, failed, etc.)
            search_term: Text to search for in messages
            start_time: Filter logs after this timestamp (Unix timestamp)
            end_time: Filter logs before this timestamp (Unix timestamp)
            
        Returns:
            Filtered list of log dictionaries
        """
        filtered_logs = logs
        
        if level:
            level_upper = level.upper()
            filtered_logs = [log for log in filtered_logs 
                           if log['level'].upper() == level_upper]
        
        if task_id:
            filtered_logs = [log for log in filtered_logs 
                           if log['task_id'] and task_id.lower() in log['task_id'].lower()]
        
        if status:
            filtered_logs = [log for log in filtered_logs 
                           if log['status'] and status.lower() in log['status'].lower()]
        
        if search_term:
            search_lower = search_term.lower()
            filtered_logs = [log for log in filtered_logs 
                           if search_lower in log['message'].lower() or 
                              (log['task_id'] and search_lower in log['task_id'].lower())]
        
        if start_time:
            filtered_logs = [log for log in filtered_logs 
                           if log.get('received_at', 0) >= start_time]
        
        if end_time:
            filtered_logs = [log for log in filtered_logs 
                           if log.get('received_at', float('inf')) <= end_time]
        
        return filtered_logs
    
    def get_recent_logs(self, log_path: Path, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get the most recent log entries from a file.
        
        Args:
            log_path: Path to log file
            count: Number of recent entries to return
            
        Returns:
            List of parsed log dictionaries
        """
        if log_path in self.stream_buffers:
            # Use the streaming buffer if available
            buffer = self.stream_buffers[log_path]
            recent_entries = list(buffer)[-count:] if len(buffer) > count else list(buffer)
            return recent_entries
        
        # Fallback to reading from file
        lines = self.read_log_file(log_path, max_lines=count)
        result = []
        for line in lines:
            parsed = self.parse_log_line(line)
            if parsed:
                parsed['file_path'] = str(log_path)
                parsed['received_at'] = time.time()
                result.append(parsed)
        return result
    
    def get_streaming_logs(self, log_path: Path, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get logs from the streaming buffer.
        
        Args:
            log_path: Path to log file
            count: Number of recent entries to return
            
        Returns:
            List of parsed log dictionaries from the streaming buffer
        """
        if log_path in self.stream_buffers:
            buffer = self.stream_buffers[log_path]
            return list(buffer)[-count:] if len(buffer) > count else list(buffer)
        return []
    
    def analyze_workflow_status(self, log_path: Path) -> Dict[str, Any]:
        """
        Analyze workflow status from log file.
        
        Args:
            log_path: Path to log file
            
        Returns:
            Dictionary with workflow status analysis
        """
        logs = self.get_recent_logs(log_path, count=1000)  # Analyze last 1000 lines
        
        status_counts = {'succeeded': 0, 'failed': 0, 'submitted': 0, 'running': 0}
        tasks = set()
        cycles = set()
        
        for log in logs:
            if log['task_id']:
                tasks.add(log['task_id'])
            if log['cycle']:
                cycles.add(log['cycle'])
            
            if log['status']:
                for status_key in status_counts:
                    if status_key in log['status'].lower():
                        status_counts[status_key] += 1
        
        return {
            'total_tasks': len(tasks),
            'active_cycles': len(cycles),
            'status_counts': status_counts,
            'last_updated': datetime.now() if logs else None,
            'recent_errors': [log for log in logs if log['level'] == 'ERROR'][:10]
        }
    
    def get_log_statistics(self, log_path: Path) -> Dict[str, Any]:
        """
        Get statistics about a log file.
        
        Args:
            log_path: Path to log file
            
        Returns:
            Dictionary with log statistics
        """
        file_size = FileUtils.get_file_size(log_path)
        line_count = 0
        level_counts = {'INFO': 0, 'WARNING': 0, 'ERROR': 0, 'DEBUG': 0}
        
        # For efficiency, we'll sample the file instead of reading all lines
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f):
                    if line_num % 100 == 0:  # Sample every 100th line
                        parsed = self.parse_log_line(line)
                        if parsed['level'] in level_counts:
                            level_counts[parsed['level']] += 1
                    line_count += 1
        except Exception as e:
            self.logger.error(f"Error getting log statistics for {log_path}: {str(e)}")
        
        return {
            'file_size': file_size,
            'estimated_line_count': line_count,
            'level_counts': level_counts,
            'last_modified': log_path.stat().st_mtime if log_path.exists() else None
        }


class LogProcessor:
    """
    Handles processing of workflow logs with filtering and formatting capabilities.
    """
    
    def __init__(self, config):
        """
        Initialize the log processor with configuration.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.streaming_processor = StreamingLogProcessor(config)
        
        # Common log patterns for Rocoto workflows
        self.patterns = Settings().LOG_PATTERNS
    
    def register_stream_callback(self, log_path: Path, callback: Callable[[Dict[str, Any]], None]):
        """
        Register a callback to receive real-time log updates.
        
        Args:
            log_path: Path to the log file
            callback: Function to call when new log entries are available
        """
        return self.streaming_processor.register_stream_callback(log_path, callback)
    
    def unregister_stream_callback(self, log_path: Path, callback: Callable[[Dict[str, Any]], None]):
        """
        Unregister a callback from receiving real-time log updates.
        
        Args:
            log_path: Path to the log file
            callback: Function to remove from callbacks
        """
        return self.streaming_processor.unregister_stream_callback(log_path, callback)
    
    def process_new_log_line(self, log_path: Path, line: str) -> Optional[Dict[str, Any]]:
        """
        Process a new log line in real-time.
        
        Args:
            log_path: Path to the log file
            line: New log line to process
            
        Returns:
            Parsed log entry or None if parsing failed
        """
        return self.streaming_processor.process_new_log_line(log_path, line)
    
    def read_log_file(self, log_path: Path, max_lines: Optional[int] = None) -> List[str]:
        """
        Read log file with optional line limit.
        
        Args:
            log_path: Path to log file
            max_lines: Maximum number of lines to read (from end)
            
        Returns:
            List of log lines
        """
        return self.streaming_processor.read_log_file(log_path, max_lines)
    
    def parse_log_line(self, line: str) -> Dict[str, Any]:
        """
        Parse a single log line into structured data.
        
        Args:
            line: Log line to parse
            
        Returns:
            Dictionary with parsed log data
        """
        return self.streaming_processor.parse_log_line(line)
    
    def filter_logs(self, logs: List[Dict[str, Any]], 
                   level: Optional[str] = None,
                   task_id: Optional[str] = None,
                   status: Optional[str] = None,
                   search_term: Optional[str] = None,
                   start_time: Optional[float] = None,
                   end_time: Optional[float] = None) -> List[Dict[str, Any]]:
        """
        Filter logs based on various criteria.
        
        Args:
            logs: List of parsed log dictionaries
            level: Log level to filter (INFO, WARNING, ERROR, DEBUG)
            task_id: Task ID to filter
            status: Status to filter (succeeded, failed, etc.)
            search_term: Text to search for in messages
            start_time: Filter logs after this timestamp (Unix timestamp)
            end_time: Filter logs before this timestamp (Unix timestamp)
            
        Returns:
            Filtered list of log dictionaries
        """
        return self.streaming_processor.filter_logs(logs, level, task_id, status, 
                                                   search_term, start_time, end_time)
    
    def get_recent_logs(self, log_path: Path, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get the most recent log entries from a file.
        
        Args:
            log_path: Path to log file
            count: Number of recent entries to return
            
        Returns:
            List of parsed log dictionaries
        """
        return self.streaming_processor.get_recent_logs(log_path, count)
    
    def get_streaming_logs(self, log_path: Path, count: int = 100) -> List[Dict[str, Any]]:
        """
        Get logs from the streaming buffer.
        
        Args:
            log_path: Path to log file
            count: Number of recent entries to return
            
        Returns:
            List of parsed log dictionaries from the streaming buffer
        """
        return self.streaming_processor.get_streaming_logs(log_path, count)
    
    def analyze_workflow_status(self, log_path: Path) -> Dict[str, Any]:
        """
        Analyze workflow status from log file.
        
        Args:
            log_path: Path to log file
            
        Returns:
            Dictionary with workflow status analysis
        """
        return self.streaming_processor.analyze_workflow_status(log_path)
    
    def get_log_statistics(self, log_path: Path) -> Dict[str, Any]:
        """
        Get statistics about a log file.
        
        Args:
            log_path: Path to log file
            
        Returns:
            Dictionary with log statistics
        """
        return self.streaming_processor.get_log_statistics(log_path)