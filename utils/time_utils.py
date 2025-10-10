"""
Time utilities module for RocotoViewer.

This module provides common time operations and utilities used throughout the application.
"""

from datetime import datetime, timedelta
from typing import Union, Optional
import time
import logging


class TimeUtils:
    """
    Utility class for time operations.
    """
    
    logger = logging.getLogger(__name__)
    
    @staticmethod
    def format_timestamp(timestamp: Union[datetime, float], 
                        format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
        """
        Format a timestamp into a readable string.
        
        Args:
            timestamp: DateTime object or Unix timestamp
            format_str: Format string for output
            
        Returns:
            Formatted timestamp string
        """
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, datetime):
            dt = timestamp
        else:
            raise ValueError(f"Invalid timestamp type: {type(timestamp)}")
        
        return dt.strftime(format_str)
    
    @staticmethod
    def parse_timestamp(timestamp_str: str, 
                       format_str: Optional[str] = None) -> Optional[datetime]:
        """
        Parse a timestamp string into a datetime object.
        
        Args:
            timestamp_str: Timestamp string to parse
            format_str: Expected format string (if None, tries common formats)
            
        Returns:
            Parsed datetime object or None if parsing fails
        """
        if format_str:
            try:
                return datetime.strptime(timestamp_str, format_str)
            except ValueError:
                return None
        
        # Try common formats
        common_formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d",
            "%H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S"
        ]
        
        for fmt in common_formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue
        
        TimeUtils.logger.warning(f"Could not parse timestamp: {timestamp_str}")
        return None
    
    @staticmethod
    def get_time_difference(start_time: Union[datetime, float], 
                           end_time: Union[datetime, float]) -> timedelta:
        """
        Calculate the difference between two timestamps.
        
        Args:
            start_time: Start time (datetime or Unix timestamp)
            end_time: End time (datetime or Unix timestamp)
            
        Returns:
            Time difference as timedelta
        """
        if isinstance(start_time, (int, float)):
            start_dt = datetime.fromtimestamp(start_time)
        else:
            start_dt = start_time
            
        if isinstance(end_time, (int, float)):
            end_dt = datetime.fromtimestamp(end_time)
        else:
            end_dt = end_time
        
        return end_dt - start_dt
    
    @staticmethod
    def is_timestamp_recent(timestamp: Union[datetime, float], 
                           seconds: int = 300) -> bool:  # 5 minutes default
        """
        Check if a timestamp is within the specified number of seconds from now.
        
        Args:
            timestamp: Timestamp to check
            seconds: Number of seconds to consider "recent"
            
        Returns:
            True if timestamp is recent, False otherwise
        """
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
        else:
            dt = timestamp
        
        time_diff = abs((datetime.now() - dt).total_seconds())
        return time_diff <= seconds
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """
        Format a duration in seconds into a human-readable string.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if seconds < 0:
            return f"-{TimeUtils.format_duration(-seconds)}"
        
        if seconds < 1:
            return f"{seconds:.3f}s"
        
        if seconds < 60:
            return f"{seconds:.1f}s"
        
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        
        if minutes < 60:
            return f"{int(minutes)}m {remaining_seconds:.1f}s"
        
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        if hours < 24:
            return f"{int(hours)}h {int(remaining_minutes)}m {remaining_seconds:.1f}s"
        
        days = hours // 24
        remaining_hours = hours % 24
        
        return f"{int(days)}d {int(remaining_hours)}h {int(remaining_minutes)}m"
    
    @staticmethod
    def sleep_interruptible(seconds: float, check_interval: float = 0.1) -> bool:
        """
        Sleep for a specified number of seconds, but allow interruption.
        
        Args:
            seconds: Number of seconds to sleep
            check_interval: Interval to check for interruption
            
        Returns:
            True if sleep completed, False if interrupted
        """
        start_time = time.time()
        end_time = start_time + seconds
        
        while time.time() < end_time:
            time.sleep(min(check_interval, end_time - time.time()))
            
            # Check for interruption (in a real implementation, this might check
            # for a stop event or other interrupt mechanism)
            # For now, we'll just return True as there's no actual interruption mechanism
            pass
        
        return True
    
    @staticmethod
    def get_current_unix_timestamp() -> float:
        """
        Get the current Unix timestamp.
        
        Returns:
            Current Unix timestamp as float
        """
        return time.time()
    
    @staticmethod
    def get_current_iso_timestamp() -> str:
        """
        Get the current time as ISO format string.
        
        Returns:
            Current time as ISO format string
        """
        return datetime.now().isoformat()
    
    @staticmethod
    def get_future_timestamp(seconds: int) -> float:
        """
        Get a timestamp for a future time.
        
        Args:
            seconds: Number of seconds in the future
            
        Returns:
            Future Unix timestamp
        """
        return time.time() + seconds
    
    @staticmethod
    def get_past_timestamp(seconds: int) -> float:
        """
        Get a timestamp for a past time.
        
        Args:
            seconds: Number of seconds in the past
            
        Returns:
            Past Unix timestamp
        """
        return time.time() - seconds