"""
Formatting utilities module for RocotoViewer.

This module provides common formatting functions used throughout the application.
"""

from typing import Any, Dict, List, Union, Optional
import json
import logging


class FormattingUtils:
    """
    Utility class for formatting operations.
    """
    
    logger = logging.getLogger(__name__)
    
    @staticmethod
    def format_workflow_status(status: str) -> str:
        """
        Format workflow status for display.
        
        Args:
            status: Raw workflow status
            
        Returns:
            Formatted status string
        """
        status_mapping = {
            'S': 'SUCCESS',
            'F': 'FAILED', 
            'R': 'RUNNING',
            'Q': 'QUEUED',
            'H': 'HELD',
            'U': 'UNKNOWN',
            'succeeded': 'SUCCESS',
            'failed': 'FAILED',
            'running': 'RUNNING',
            'submitted': 'QUEUED',
            'active': 'ACTIVE',
            'inactive': 'INACTIVE'
        }
        
        formatted_status = status_mapping.get(status.upper(), status.upper())
        
        # Add color codes or styling based on status
        if formatted_status in ['SUCCESS', 'RUNNING']:
            return f"[green]{formatted_status}[/green]"
        elif formatted_status in ['FAILED', 'ERROR']:
            return f"[red]{formatted_status}[/red]"
        elif formatted_status in ['QUEUED', 'HELD']:
            return f"[yellow]{formatted_status}[/yellow]"
        else:
            return f"[blue]{formatted_status}[/blue]"
    
    @staticmethod
    def format_task_summary(tasks: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Create a summary of task statuses.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            Dictionary with status counts
        """
        summary = {
            'total': len(tasks),
            'success': 0,
            'failed': 0,
            'running': 0,
            'queued': 0,
            'held': 0,
            'unknown': 0
        }
        
        status_map = {
            'S': 'success',
            'F': 'failed',
            'R': 'running', 
            'Q': 'queued',
            'H': 'held'
        }
        
        for task in tasks:
            status = task.get('status', 'U').upper()
            status_key = status_map.get(status, 'unknown')
            summary[status_key] += 1
        
        return summary
    
    @staticmethod
    def format_json(data: Any, indent: int = 2) -> str:
        """
        Format data as indented JSON string.
        
        Args:
            data: Data to format as JSON
            indent: Number of spaces for indentation
            
        Returns:
            Formatted JSON string
        """
        try:
            return json.dumps(data, indent=indent, default=str, ensure_ascii=False)
        except Exception as e:
            FormattingUtils.logger.error(f"Error formatting JSON: {str(e)}")
            return str(data)
    
    @staticmethod
    def format_percentage(value: float, total: float, decimals: int = 2) -> str:
        """
        Format a value as a percentage of a total.
        
        Args:
            value: Value to calculate percentage for
            total: Total value
            decimals: Number of decimal places
            
        Returns:
            Formatted percentage string
        """
        if total == 0:
            return "0.00%"
        
        percentage = (value / total) * 100
        return f"{percentage:.{decimals}f}%"
    
    @staticmethod
    def format_bytes(bytes_value: Union[int, float], 
                    decimal_places: int = 2) -> str:
        """
        Format a byte value into human-readable format.
        
        Args:
            bytes_value: Number of bytes
            decimal_places: Number of decimal places in result
            
        Returns:
            Formatted byte string (e.g., "1.23 KB", "4.56 MB")
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.{decimal_places}f} {unit}"
            bytes_value /= 1024.0
        
        return f"{bytes_value:.{decimal_places}f} PB"
    
    @staticmethod
    def format_duration(seconds: Union[int, float]) -> str:
        """
        Format a duration in seconds into human-readable format.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if seconds < 0:
            return f"-{FormattingUtils.format_duration(-seconds)}"
        
        if seconds < 1:
            return f"{seconds:.3f}s"
        
        if seconds < 60:
            return f"{seconds:.1f}s"
        
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        
        if minutes < 60:
            return f"{minutes}m {remaining_seconds:.1f}s"
        
        hours = int(minutes // 60)
        remaining_minutes = minutes % 60
        
        if hours < 24:
            return f"{hours}h {remaining_minutes}m {remaining_seconds:.1f}s"
        
        days = int(hours // 24)
        remaining_hours = hours % 24
        
        return f"{days}d {remaining_hours}h {remaining_minutes}m"
    
    @staticmethod
    def format_table(data: List[Dict[str, Any]], 
                    columns: Optional[List[str]] = None,
                    headers: Optional[Dict[str, str]] = None) -> str:
        """
        Format data as a text table.
        
        Args:
            data: List of dictionaries to format as table
            columns: List of column keys to include (if None, uses all keys)
            headers: Dictionary mapping column keys to display headers
            
        Returns:
            Formatted table string
        """
        if not data:
            return "No data to display"
        
        # Determine columns to display
        if columns is None:
            columns = list(data[0].keys()) if data else []
        
        # Determine headers
        if headers is None:
            headers = {col: col.title() for col in columns}
        
        # Calculate column widths
        col_widths = {}
        for col in columns:
            header_width = len(headers.get(col, col))
            max_data_width = max(len(str(row.get(col, ""))) for row in data)
            col_widths[col] = max(header_width, max_data_width) + 2  # Add padding
        
        # Create header row
        header_row = "|"
        for col in columns:
            header = headers.get(col, col)
            header_row += f" {header:<{col_widths[col]-1}}|"
        
        # Create separator row
        separator_row = "|"
        for col in columns:
            separator_row += f"{'-' * col_widths[col]}|"
        
        # Create data rows
        data_rows = []
        for row in data:
            data_row = "|"
            for col in columns:
                value = str(row.get(col, ""))
                data_row += f" {value:<{col_widths[col]-1}}|"
            data_rows.append(data_row)
        
        # Combine all rows
        table_lines = [header_row, separator_row] + data_rows
        return "\n".join(table_lines)
    
    @staticmethod
    def format_log_entry(entry: Dict[str, Any], 
                        include_timestamp: bool = True,
                        include_level: bool = True) -> str:
        """
        Format a log entry for display.
        
        Args:
            entry: Log entry dictionary
            include_timestamp: Whether to include timestamp
            include_level: Whether to include log level
            
        Returns:
            Formatted log entry string
        """
        parts = []
        
        if include_timestamp and 'timestamp' in entry:
            timestamp = entry['timestamp']
            if hasattr(timestamp, 'strftime'):
                timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp_str = str(timestamp)
            parts.append(f"[{timestamp_str}]")
        
        if include_level and 'level' in entry:
            level = entry['level']
            parts.append(f"[{level}]")
        
        if 'message' in entry:
            parts.append(entry['message'])
        
        return " ".join(parts)
    
    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """
        Truncate text to a maximum length.
        
        Args:
            text: Text to truncate
            max_length: Maximum length of result
            suffix: Suffix to add to truncated text
            
        Returns:
            Truncated text string
        """
        if len(text) <= max_length:
            return text
        
        suffix_length = len(suffix)
        if max_length <= suffix_length:
            return suffix[:max_length]
        
        return text[:max_length - suffix_length] + suffix