"""
Status visualization utilities for RocotoViewer.

This module provides utilities for visualizing workflow and task statuses
with color coding, progress tracking, and other visual indicators.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime
from textual.widgets import ProgressBar
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
import logging

from .formatting import FormattingUtils


class StatusVisualization:
    """
    Utility class for status visualization in RocotoViewer.
    """
    
    logger = logging.getLogger(__name__)
    
    # Status color mapping
    STATUS_COLORS = {
        'SUCCESS': 'green',
        'SUCCEEDED': 'green',
        'COMPLETED': 'green',
        'RUNNING': 'blue',
        'ACTIVE': 'blue',
        'R': 'blue',
        'FAILED': 'red',
        'ERROR': 'red',
        'F': 'red',
        'QUEUED': 'yellow',
        'PENDING': 'yellow',
        'Q': 'yellow',
        'HELD': 'orange',
        'H': 'orange',
        'UNKNOWN': 'gray',
        'U': 'gray',
        'SUBMITTED': 'cyan',
        'INACTIVE': 'gray'
    }
    
    # Status symbols
    STATUS_SYMBOLS = {
        'SUCCESS': '✅',
        'SUCCEEDED': '✅',
        'COMPLETED': '✅',
        'RUNNING': '🏃',
        'ACTIVE': '🏃',
        'R': '🏃',
        'FAILED': '❌',
        'ERROR': '❌',
        'F': '❌',
        'QUEUED': '⏳',
        'PENDING': '⏳',
        'Q': '⏳',
        'HELD': '⏸️',
        'H': '⏸️',
        'UNKNOWN': '❓',
        'U': '❓',
        'SUBMITTED': '📤',
        'INACTIVE': '⭕'
    }
    
    @classmethod
    def get_status_color(cls, status: str) -> str:
        """
        Get the color for a given status.
        
        Args:
            status: Status string
            
        Returns:
            Color name for the status
        """
        status_upper = status.upper()
        return cls.STATUS_COLORS.get(status_upper, 'gray')
    
    @classmethod
    def get_status_symbol(cls, status: str) -> str:
        """
        Get the symbol for a given status.
        
        Args:
            status: Status string
            
        Returns:
            Symbol for the status
        """
        status_upper = status.upper()
        return cls.STATUS_SYMBOLS.get(status_upper, '❓')
    
    @classmethod
    def format_status_text(cls, status: str, include_symbol: bool = True) -> Text:
        """
        Format status text with color and symbol.
        
        Args:
            status: Status string
            include_symbol: Whether to include symbol
            
        Returns:
            Formatted Text object
        """
        color = cls.get_status_color(status)
        symbol = cls.get_status_symbol(status) if include_symbol else ''
        
        if include_symbol:
            return Text(f"{symbol} {status.upper()}", style=f"bold {color}")
        else:
            return Text(status.upper(), style=f"bold {color}")
    
    @classmethod
    def calculate_workflow_progress(cls, tasks: List[Dict[str, Any]]) -> Tuple[float, Dict[str, int]]:
        """
        Calculate workflow progress based on task statuses.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            Tuple of (progress_percentage, status_counts)
        """
        if not tasks:
            return 0.0, {}
        
        status_counts = {}
        for task in tasks:
            status = task.get('status', 'UNKNOWN').upper()
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Calculate progress: completed tasks / total tasks
        total = len(tasks)
        completed = 0
        
        for status in ['SUCCESS', 'SUCCEEDED', 'COMPLETED', 'FAILED', 'ERROR']:
            completed += status_counts.get(status, 0)
        
        progress = (completed / total) * 100 if total > 0 else 0.0
        return min(progress, 10.0), status_counts
    
    @classmethod
    def create_progress_bar(cls, tasks: List[Dict[str, Any]], width: int = 40) -> str:
        """
        Create a text-based progress bar for workflow progress.
        
        Args:
            tasks: List of task dictionaries
            width: Width of the progress bar
            
        Returns:
            String representation of progress bar
        """
        progress_percent, status_counts = cls.calculate_workflow_progress(tasks)
        
        # Calculate filled and empty sections
        filled_chars = int((progress_percent / 100) * width)
        empty_chars = width - filled_chars
        
        # Create progress bar
        filled = '█' * filled_chars
        empty = '░' * empty_chars
        
        # Add color based on progress
        if progress_percent >= 80:
            bar_color = 'green'
        elif progress_percent >= 50:
            bar_color = 'yellow'
        elif progress_percent >= 20:
            bar_color = 'orange'
        else:
            bar_color = 'red'
        
        return f"[{bar_color}]{filled}{empty}[/] {progress_percent:.1f}%"
    
    @classmethod
    def create_status_summary_table(cls, tasks: List[Dict[str, Any]]) -> Table:
        """
        Create a Rich table showing status summary.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            Rich Table object
        """
        table = Table(title="Task Status Summary", show_header=True, header_style="bold magenta")
        table.add_column("Status", style="dim")
        table.add_column("Count", justify="right")
        table.add_column("Percentage", justify="right")
        
        if not tasks:
            table.add_row("No tasks", "0", "0.0%")
            return table
        
        # Count statuses
        status_counts = {}
        for task in tasks:
            status = task.get('status', 'UNKNOWN').upper()
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total = len(tasks)
        
        # Add rows for each status
        for status, count in status_counts.items():
            percentage = (count / total) * 100 if total > 0 else 0
            color = cls.get_status_color(status)
            symbol = cls.get_status_symbol(status)
            table.add_row(f"[{color}]{symbol} {status}[/]", str(count), f"{percentage:.1f}%")
        
        # Add total row
        table.add_row("[bold]TOTAL[/]", str(total), "100.0%")
        
        return table
    
    @classmethod
    def format_task_duration(cls, start_time: str, end_time: str) -> str:
        """
        Format the duration between start and end times.
        
        Args:
            start_time: Start time in ISO format
            end_time: End time in ISO format
            
        Returns:
            Formatted duration string
        """
        if not start_time or not end_time or start_time == 'N/A' or end_time == 'N/A':
            return 'N/A'
        
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            duration = end_dt - start_dt
            return FormattingUtils.format_duration(duration.total_seconds())
        except Exception as e:
            cls.logger.error(f"Error calculating duration: {str(e)}")
            return 'N/A'
    
    @classmethod
    def get_task_health_score(cls, tasks: List[Dict[str, Any]]) -> float:
        """
        Calculate a health score for the workflow based on task statuses.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            Health score from 0 to 100
        """
        if not tasks:
            return 0.0
        
        status_counts = {}
        for task in tasks:
            status = task.get('status', 'UNKNOWN').upper()
            status_counts[status] = status_counts.get(status, 0) + 1
        
        total = len(tasks)
        
        # Assign weights to different statuses
        score = 0.0
        score += status_counts.get('SUCCESS', 0) * 1.0  # Success = full points
        score += status_counts.get('SUCCEEDED', 0) * 1.0
        score += status_counts.get('COMPLETED', 0) * 1.0
        score += status_counts.get('RUNNING', 0) * 0.7  # Running = partial points
        score += status_counts.get('ACTIVE', 0) * 0.7
        score += status_counts.get('QUEUED', 0) * 0.5  # Queued = partial points
        score += status_counts.get('PENDING', 0) * 0.5
        score += status_counts.get('SUBMITTED', 0) * 0.5
        score += status_counts.get('HELD', 0) * 0.2  # Held = low points
        score += status_counts.get('FAILED', 0) * 0.0  # Failed = no points
        score += status_counts.get('ERROR', 0) * 0.0
        score += status_counts.get('UNKNOWN', 0) * 0.1  # Unknown = minimal points
        
        return (score / total) * 100 if total > 0 else 0.0
    
    @classmethod
    def create_visual_status_bar(cls, tasks: List[Dict[str, Any]], width: int = 60) -> str:
        """
        Create a visual status bar showing the distribution of task statuses.
        
        Args:
            tasks: List of task dictionaries
            width: Width of the status bar
            
        Returns:
            String representation of status bar
        """
        if not tasks:
            return "No tasks to display"
        
        # Count statuses
        status_counts = {}
        for task in tasks:
            status = task.get('status', 'UNKNOWN').upper()
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Calculate character distribution
        total = len(tasks)
        status_chars = []
        
        # Sort by importance
        priority_order = ['FAILED', 'ERROR', 'RUNNING', 'ACTIVE', 'QUEUED', 'PENDING', 'SUCCESS', 'SUCCEEDED', 'COMPLETED', 'HELD', 'UNKNOWN']
        
        for status in priority_order:
            if status in status_counts:
                count = status_counts[status]
                chars = int((count / total) * width) if total > 0 else 0
                char = cls._get_status_char(status)
                color = cls.get_status_color(status)
                status_chars.extend([f"[{color}]{char}[/{color}]" for _ in range(chars)])
        
        # Fill remaining space with empty characters if needed
        while len(status_chars) < width:
            status_chars.append(' ')
        
        return ''.join(status_chars[:width])
    
    @classmethod
    def _get_status_char(cls, status: str) -> str:
        """
        Get a single character representation for a status.
        
        Args:
            status: Status string
            
        Returns:
            Single character representation
        """
        if status in ['SUCCESS', 'SUCCEEDED', 'COMPLETED']:
            return '█'
        elif status in ['FAILED', 'ERROR']:
            return '█'
        elif status in ['RUNNING', 'ACTIVE']:
            return '▓'
        elif status in ['QUEUED', 'PENDING', 'SUBMITTED']:
            return '▒'
        elif status in ['HELD']:
            return '░'
        else:
            return '░'


# Create a singleton instance for convenience
status_visualization = StatusVisualization()