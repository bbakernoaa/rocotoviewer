"""
Log parser module for RocotoViewer.

This module parses workflow log files and extracts structured information
with backward compatibility for legacy log formats.
"""

import re
from pathlib import Path
from typing import Any, Dict, List
import logging
from datetime import datetime

from .base_parser import BaseParser


class LogParser(BaseParser):
    """
    Parser for workflow log files with backward compatibility for legacy formats.
    """
    
    def __init__(self, config=None):
        """
        Initialize the log parser.
        
        Args:
            config: Application configuration
        """
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Common log patterns for Rocoto workflows (current format)
        self.patterns = {
            'timestamp': r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}',
            'task_status': r'(?:INFO|WARN|ERROR|DEBUG).*?(?:succeeded|failed|submitted|running)',
            'cycle_info': r'cycle=(\d+)',
            'task_id': r'task=([a-zA-Z0-9_]+)',
            'job_id': r'jobid=([0-9]+)',
            'exit_code': r'exit\s*:\s*(\d+)',
        }
        
        # Legacy log patterns for backward compatibility
        self.legacy_patterns = {
            'timestamp_v1': r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',
            'timestamp_v2': r'\w{3} \d{2} \d{2}:\d{2}:\d{2} \d{4}',
            'task_status_legacy': r'(?:TASK|JOB).*?(?:SUCCESS|FAIL|RUN|QUEUE)',
            'cycle_info_legacy': r'CYCLE.*?(\d+)',
            'task_id_legacy': r'NAME.*?([a-zA-Z0-9_]+)',
            'job_id_legacy': r'ID.*?([0-9]+)',
            'exit_code_legacy': r'CODE.*?(\d+)',
        }
    
    def parse(self, source: str) -> Dict[str, Any]:
        """
        Parse a log file and extract structured information with backward compatibility.
        
        Args:
            source: Path to the log file
            
        Returns:
            Dictionary with parsed log data
        """
        if not self.validate_source(source):
            return {}
        
        # Detect format version for backward compatibility
        format_info = self.detect_format_version(source)
        self.logger.info(f"Detected format: {format_info}")
        
        content = self.read_file(source)
        if content is None:
            return {}
        
        try:
            lines = content.splitlines()
            parsed_logs = []
            
            for line_num, line in enumerate(lines, 1):
                parsed_line = self._parse_log_line(line, line_num, format_info)
                if parsed_line:
                    parsed_logs.append(parsed_line)
            
            return {
                'source': source,
                'total_lines': len(lines),
                'parsed_lines': len(parsed_logs),
                'logs': parsed_logs,
                'format_info': format_info,
                'parsed_at': datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error parsing log file {source}: {str(e)}")
            
            # Try legacy parsing as fallback
            try:
                lines = content.splitlines()
                parsed_logs = []
                
                for line_num, line in enumerate(lines, 1):
                    parsed_line = self._parse_legacy_log_line(line, line_num)
                    if parsed_line:
                        parsed_logs.append(parsed_line)
                
                return {
                    'source': source,
                    'total_lines': len(lines),
                    'parsed_lines': len(parsed_logs),
                    'logs': parsed_logs,
                    'format_info': {'format': 'legacy', 'version': 'unknown', 'confidence': 1.0, 'parser_strategy': 'legacy'},
                    'parsed_at': datetime.now().isoformat()
                }
            except Exception as fallback_e:
                self.logger.error(f"Fallback parsing also failed: {str(fallback_e)}")
                return {}
    
    def _parse_log_line(self, line: str, line_number: int, format_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a single log line into structured data with format-specific handling.
        
        Args:
            line: Log line to parse
            line_number: Line number in the file
            format_info: Format detection information
            
        Returns:
            Dictionary with parsed log data
        """
        if format_info.get('parser_strategy') == 'legacy':
            return self._parse_legacy_log_line(line, line_number)
        
        result = {
            'line_number': line_number,
            'raw': line,
            'timestamp': None,
            'level': 'INFO',
            'message': line,
            'task_id': None,
            'cycle': None,
            'job_id': None,
            'exit_code': None,
            'status': None
        }
        
        # Extract timestamp
        timestamp_match = re.search(self.patterns['timestamp'], line)
        if timestamp_match:
            try:
                result['timestamp'] = datetime.strptime(timestamp_match.group(), '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass # If timestamp format is unexpected, leave as None
        
        # Extract task ID
        task_match = re.search(self.patterns['task_id'], line)
        if task_match:
            result['task_id'] = task_match.group(1)
        
        # Extract cycle info
        cycle_match = re.search(self.patterns['cycle_info'], line)
        if cycle_match:
            result['cycle'] = cycle_match.group(1)
        
        # Extract job ID
        job_match = re.search(self.patterns['job_id'], line)
        if job_match:
            result['job_id'] = job_match.group(1)
        
        # Extract exit code
        exit_match = re.search(self.patterns['exit_code'], line)
        if exit_match:
            result['exit_code'] = exit_match.group(1)
        
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
        
        # Extract the main message part
        message = line
        if timestamp_match:
            message = message.replace(timestamp_match.group(), '', 1).strip()
        result['message'] = message.strip()
        
        return result
    
    def _parse_legacy_log_line(self, line: str, line_number: int) -> Dict[str, Any]:
        """
        Parse a single log line in legacy format into structured data.
        
        Args:
            line: Log line to parse
            line_number: Line number in the file
            
        Returns:
            Dictionary with parsed log data
        """
        result = {
            'line_number': line_number,
            'raw': line,
            'timestamp': None,
            'level': 'INFO',
            'message': line,
            'task_id': None,
            'cycle': None,
            'job_id': None,
            'exit_code': None,
            'status': None
        }
        
        # Try legacy timestamp patterns
        for pattern_name, pattern in self.legacy_patterns.items():
            if 'timestamp' in pattern_name:
                timestamp_match = re.search(pattern, line)
                if timestamp_match:
                    try:
                        # Try different timestamp formats
                        if 'T' in timestamp_match.group():
                            result['timestamp'] = datetime.strptime(timestamp_match.group(), '%Y-%m-%dT%H:%M:%S')
                        else:
                            # Handle different legacy formats
                            try:
                                result['timestamp'] = datetime.strptime(timestamp_match.group(), '%b %d %H:%M:%S %Y')
                            except ValueError:
                                # If that fails, try other common formats
                                try:
                                    result['timestamp'] = datetime.strptime(timestamp_match.group(), '%Y-%m-%d %H:%M:%S.%f')
                                except ValueError:
                                    pass
                    except ValueError:
                        pass # If timestamp format is unexpected, leave as None
                    break
        
        # Extract task ID using legacy patterns
        for pattern_name, pattern in self.legacy_patterns.items():
            if 'task_id' in pattern_name:
                task_match = re.search(pattern, line, re.IGNORECASE)
                if task_match:
                    result['task_id'] = task_match.group(1)
                    break
        
        # Extract cycle info using legacy patterns
        for pattern_name, pattern in self.legacy_patterns.items():
            if 'cycle_info' in pattern_name:
                cycle_match = re.search(pattern, line, re.IGNORECASE)
                if cycle_match:
                    result['cycle'] = cycle_match.group(1)
                    break
        
        # Extract job ID using legacy patterns
        for pattern_name, pattern in self.legacy_patterns.items():
            if 'job_id' in pattern_name:
                job_match = re.search(pattern, line, re.IGNORECASE)
                if job_match:
                    result['job_id'] = job_match.group(1)
                    break
        
        # Extract exit code using legacy patterns
        for pattern_name, pattern in self.legacy_patterns.items():
            if 'exit_code' in pattern_name:
                exit_match = re.search(pattern, line, re.IGNORECASE)
                if exit_match:
                    result['exit_code'] = exit_match.group(1)
                    break
        
        # Extract status using legacy patterns
        for pattern_name, pattern in self.legacy_patterns.items():
            if 'task_status' in pattern_name:
                status_match = re.search(pattern, line, re.IGNORECASE)
                if status_match:
                    result['status'] = status_match.group()
                    break
        
        # Determine log level for legacy formats
        upper_line = line.upper()
        if any(err_word in upper_line for err_word in ['ERROR', 'FAIL', 'FAILED']):
            result['level'] = 'ERROR'
        elif any(warn_word in upper_line for warn_word in ['WARN', 'WARNING']):
            result['level'] = 'WARNING'
        elif 'DEBUG' in upper_line:
            result['level'] = 'DEBUG'
        elif 'INFO' in upper_line:
            result['level'] = 'INFO'
        
        # Extract the main message part
        message = line
        if result['timestamp']:
            # Remove timestamp from message
            timestamp_str = result['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            message = message.replace(timestamp_str, '', 1).strip()
        result['message'] = message.strip()
        
        return result
    
    def filter_logs(self, log_data: Dict[str, Any], 
                   level: str = None,
                   task_id: str = None,
                   status: str = None,
                   search_term: str = None) -> Dict[str, Any]:
        """
        Filter parsed logs based on criteria with backward compatibility.
        
        Args:
            log_data: Parsed log data from parse() method
            level: Filter by log level (INFO, WARNING, ERROR, DEBUG)
            task_id: Filter by task ID
            status: Filter by status
            search_term: Filter by search term in message
            
        Returns:
            Filtered log data
        """
        if 'logs' not in log_data:
            return log_data
        
        filtered_logs = log_data['logs']
        
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
        
        result = log_data.copy()
        result['logs'] = filtered_logs
        result['filtered_lines'] = len(filtered_logs)
        
        return result
    
    def get_summary(self, log_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a summary of the log data with backward compatibility.
        
        Args:
            log_data: Parsed log data from parse() method
            
        Returns:
            Summary dictionary
        """
        if 'logs' not in log_data:
            return {}
        
        logs = log_data['logs']
        
        # Count log levels
        level_counts = {}
        for log in logs:
            level = log['level']
            level_counts[level] = level_counts.get(level, 0) + 1
        
        # Extract unique task IDs
        task_ids = set()
        for log in logs:
            if log['task_id']:
                task_ids.add(log['task_id'])
        
        # Find first and last timestamps
        timestamps = [log['timestamp'] for log in logs if log['timestamp']]
        first_timestamp = min(timestamps) if timestamps else None
        last_timestamp = max(timestamps) if timestamps else None
        
        return {
            'total_logs': len(logs),
            'level_counts': level_counts,
            'unique_tasks': len(task_ids),
            'first_timestamp': first_timestamp.isoformat() if first_timestamp else None,
            'last_timestamp': last_timestamp.isoformat() if last_timestamp else None,
            'has_errors': level_counts.get('ERROR', 0) > 0,
            'format_info': log_data.get('format_info', {})
        }