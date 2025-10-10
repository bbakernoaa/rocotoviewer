"""
Log viewer widget module for RocotoViewer Textual UI.

This module provides a widget for displaying log information with real-time updates.
"""

from typing import Any, Dict, List, Optional
import logging
import asyncio
from collections import deque

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, DataTable, Input, Button, Checkbox, Label
from textual.reactive import reactive
from textual.message import Message
from textual.timer import Timer

from ...config.config import Config
from ...core.state_manager import StateManager
from ...core.log_processor import LogProcessor
from ...parsers.workflow_parser import WorkflowParser


class LogViewer(Container):
    """
    Widget for displaying log information in the UI with real-time updates.
    """
    
    # Reactive attributes
    log_entries = reactive([])
    selected_log_entry = reactive(None)
    
    def __init__(self, config: Config, state_manager: StateManager, 
                 log_processor: LogProcessor, workflow_parser: WorkflowParser):
        """
        Initialize the log viewer widget.
        
        Args:
            config: Application configuration
            state_manager: State manager instance
            log_processor: Log processor instance
            workflow_parser: Workflow parser instance
        """
        super().__init__()
        
        self.config = config
        self.state_manager = state_manager
        self.log_processor = log_processor
        self.workflow_parser = workflow_parser
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Current display settings
        self.max_lines = config.display.max_log_lines if config else 1000
        self.auto_scroll = True
        self.is_paused = False
        
        # Initialize widgets
        self.log_table = DataTable(id="log-table")
        self.log_details = Static(id="log-details", classes="log-details")
        self.status_label = Label("Real-time updates: ON", id="status-label")
        
        # Set up the log table
        self.log_table.cursor_type = "row"
        self.log_table.add_column("Time", key="timestamp", width=18)
        self.log_table.add_column("Level", key="level", width=8)
        self.log_table.add_column("Task", key="task_id", width=15)
        self.log_table.add_column("Status", key="status", width=12)
        self.log_table.add_column("Message", key="message")
        
        # Buffer for real-time updates
        self.log_buffer = deque(maxlen=self.max_lines)
        
        # Register callback for real-time log updates
        self._register_log_callbacks()
    
    def _register_log_callbacks(self):
        """Register callbacks for real-time log updates."""
        # This would register with the event bus or log processor
        # to receive real-time log updates
        pass
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the log viewer."""
        yield Vertical(
            Horizontal(
                Static("Log Entries", classes="section-title"),
                self.status_label,
                Button("Clear Filters", id="clear-filters-btn", variant="warning"),
                Button("Pause", id="pause-btn", variant="primary"),
                Button("Clear", id="clear-btn", variant="error"),
                id="log-header"
            ),
            self.log_table,
            self.log_details,
            id="log-viewer-container"
        )
    
    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        # Initialize with empty table
        self.update_logs([])
        
        # Start periodic refresh if needed
        self._start_periodic_refresh()
    
    def _start_periodic_refresh(self):
        """Start periodic refresh of log data."""
        # Set up a timer to periodically check for new logs
        self.refresh_timer = self.set_interval(1.0, self._periodic_refresh)
    
    def _periodic_refresh(self):
        """Periodic refresh of log data."""
        if not self.is_paused:
            self.refresh()
    
    def update_logs(self, log_entries: List[Dict[str, Any]]) -> None:
        """
        Update the log viewer with new log data.
        
        Args:
            log_entries: List of log entries to display
        """
        self.log_entries = log_entries
        self._update_log_table()
    
    def add_log_entry(self, log_entry: Dict[str, Any]) -> None:
        """
        Add a single log entry in real-time.
        
        Args:
            log_entry: Single log entry to add
        """
        if not self.is_paused:
            # Add to buffer
            self.log_buffer.append(log_entry)
            
            # Update the table immediately
            self._add_log_row(log_entry)
            
            # Auto-scroll to the bottom if enabled
            if self.auto_scroll:
                self._scroll_to_bottom()
    
    def _add_log_row(self, log_entry: Dict[str, Any]) -> None:
        """Add a single row to the log table."""
        timestamp = log_entry.get('timestamp', 'N/A')[:19] if log_entry.get('timestamp') else 'N/A'
        level = log_entry.get('level', 'INFO')
        task_id = log_entry.get('task_id', 'N/A')
        status = log_entry.get('status', 'N/A')
        message = log_entry.get('message', 'No message')
        
        # Color code based on log level
        level_display = f"[red]{level}[/red]" if level == "ERROR" else \
                       f"[yellow]{level}[/yellow]" if level == "WARNING" else \
                       f"[blue]{level}[/blue]" if level == "INFO" else \
                       f"[magenta]{level}[/magenta]"
        
        # Add the new row
        self.log_table.add_row(
            timestamp,
            level_display,
            task_id,
            status,
            message,
            update_widths=False  # Don't update column widths for each row
        )
        
        # Keep the table size manageable by removing old rows if needed
        if len(self.log_table.rows) > self.max_lines:
            # Remove the oldest row (first row)
            # For now, we'll clear and rebuild if too many rows
            rows_to_keep = int(self.max_lines * 0.8)  # Keep 80% of max
            current_rows = list(self.log_table.rows.values())
            if len(current_rows) > rows_to_keep:
                # Clear and rebuild with recent entries
                recent_entries = list(self.log_buffer)[-rows_to_keep:]
                self._update_log_table_with_entries(recent_entries)
    
    def _update_log_table_with_entries(self, log_entries: List[Dict[str, Any]]) -> None:
        """Update the log table with specific entries."""
        # Clear existing rows
        self.log_table.clear()
        
        # Add log rows
        for log_entry in log_entries:
            timestamp = log_entry.get('timestamp', 'N/A')[:19] if log_entry.get('timestamp') else 'N/A'
            level = log_entry.get('level', 'INFO')
            task_id = log_entry.get('task_id', 'N/A')
            status = log_entry.get('status', 'N/A')
            message = log_entry.get('message', 'No message')
            
            # Color code based on log level
            level_display = f"[red]{level}[/red]" if level == "ERROR" else \
                           f"[yellow]{level}[/yellow]" if level == "WARNING" else \
                           f"[blue]{level}[/blue]" if level == "INFO" else \
                           f"[magenta]{level}[/magenta]"
            
            self.log_table.add_row(
                timestamp,
                level_display,
                task_id,
                status,
                message
            )
    
    def _update_log_table(self) -> None:
        """Update the log table with current log entries."""
        # Clear existing rows
        self.log_table.clear()
        
        # Add log rows
        for log_entry in self.log_entries:
            timestamp = log_entry.get('timestamp', 'N/A')[:19] if log_entry.get('timestamp') else 'N/A'
            level = log_entry.get('level', 'INFO')
            task_id = log_entry.get('task_id', 'N/A')
            status = log_entry.get('status', 'N/A')
            message = log_entry.get('message', 'No message')
            
            # Color code the level in the table
            level_display = level
            
            self.log_table.add_row(
                timestamp,
                level_display,
                task_id,
                status,
                message
            )
    
    def _scroll_to_bottom(self):
        """Scroll the table to show the latest entries."""
        # For now, we'll just ensure the table shows the bottom rows
        # In a real implementation, we'd handle scrolling properly
        pass
    
    def refresh(self) -> bool:
        """
        Refresh the log display with current state data.
        
        Returns:
            True if refresh was successful
        """
        try:
            # Get recent logs from the log processor
            # In a real implementation, this would get logs from the state manager
            # or directly from monitored files
            recent_logs = []
            
            # For now, we'll just keep the current logs in the buffer
            recent_logs = list(self.log_buffer)
            
            # Update the display
            self.log_entries = recent_logs
            return True
        except Exception as e:
            self.logger.error(f"Error refreshing log viewer: {str(e)}")
            return False
    
    def watch_log_entries(self, old_value: List[Dict[str, Any]], new_value: List[Dict[str, Any]]) -> None:
        """Called when the log entries change."""
        self._update_log_table()
    
    def watch_selected_log_entry(self, old_value: Optional[Dict[str, Any]], new_value: Optional[Dict[str, Any]]) -> None:
        """Called when the selected log entry changes."""
        if new_value:
            self._update_log_details(new_value)
    
    def _update_log_details(self, log_entry: Dict[str, Any]) -> None:
        """Update the log details panel."""
        details_text = f"""
Log Entry Details:
  Timestamp: {log_entry.get('timestamp', 'N/A')}
  Level: {log_entry.get('level', 'N/A')}
  Task ID: {log_entry.get('task_id', 'N/A')}
  Status: {log_entry.get('status', 'N/A')}
  Message: {log_entry.get('message', 'N/A')}
  File: {log_entry.get('file_path', 'N/A')}
  Raw Data: {str(log_entry)}
        """.strip()
        
        self.log_details.update(details_text)
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the log table."""
        row_key = event.row_key.value
        if 0 <= row_key < len(self.log_entries):
            self.selected_log_entry = self.log_entries[row_key]
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "clear-filters-btn":
            # In a real implementation, this would clear filters
            # For now, we'll just log the action
            self.logger.info("Clear filters button pressed")
        elif event.button.id == "pause-btn":
            self.is_paused = not self.is_paused
            event.button.label = "Resume" if self.is_paused else "Pause"
            status_text = "PAUSED" if self.is_paused else "ON"
            self.status_label.update(f"Real-time updates: {status_text}")
        elif event.button.id == "clear-btn":
            # Clear the log table
            self.log_table.clear()
            self.log_buffer.clear()
    
    def handle_real_time_log(self, log_entry: Dict[str, Any]) -> None:
        """
        Handle a real-time log entry from the monitoring system.
        
        Args:
            log_entry: The log entry to display
        """
        # Add to the log viewer in real-time
        self.add_log_entry(log_entry)
    
    class LogEntrySelected(Message):
        """Message sent when a log entry is selected."""
        
        def __init__(self, log_entry: Dict[str, Any]) -> None:
            super().__init__()
            self.log_entry = log_entry
    
    class LogRefreshRequested(Message):
        """Message sent when logs need to be refreshed."""
        
        def __init__(self) -> None:
            super().__init__()
    
    class RealTimeLogAdded(Message):
        """Message sent when a real-time log is added."""
        
        def __init__(self, log_entry: Dict[str, Any]) -> None:
            super().__init__()
            self.log_entry = log_entry