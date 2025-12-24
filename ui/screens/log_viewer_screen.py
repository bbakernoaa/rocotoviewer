"""
Log viewer screen module for RocotoViewer Textual UI.

This module provides the log viewer screen interface for the application.
"""

from typing import Any, Dict, List, Optional
import logging
import asyncio

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, DataTable, Input, Button, Checkbox
from textual.reactive import reactive
from textual.message import Message

from ...config.config import Config
from ...core.state_manager import StateManager
from ...core.log_processor import StreamingLogProcessor
from ...parsers.workflow_parser import WorkflowParser
from ..widgets.log_viewer import LogViewer
from ..widgets.search_filter import SearchFilter
from ..widgets.navigation_panel import NavigationPanel


class LogViewerScreen(Container):
    """
    Log viewer screen interface for RocotoViewer.
    """
    
    # Reactive attributes
    selected_workflow_id = reactive("")
    log_entries = reactive([])
    
    def __init__(self, config: Config, state_manager: StateManager, 
                 log_processor: StreamingLogProcessor, workflow_parser: WorkflowParser):
        """
        Initialize the log viewer screen.
        
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
        
        # Initialize widgets
        self.navigation_panel = NavigationPanel(config, state_manager, log_processor, workflow_parser)
        self.search_filter = SearchFilter(config, state_manager, log_processor, workflow_parser)
        self.log_viewer_widget = LogViewer(config, state_manager, log_processor, workflow_parser)
        
        # Current filter settings
        self.filters = {
            'level': None,
            'task_id': None,
            'status': None,
            'search_term': None
        }
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the log viewer screen."""
        yield Horizontal(
            Vertical(
                self.navigation_panel,
                self.search_filter,
                id="sidebar"
            ),
            Vertical(
                Static("Log Viewer", classes="screen-title"),
                Horizontal(
                    Static("Selected Workflow:", classes="label"),
                    Static(self.selected_workflow_id or "None", id="selected-workflow", classes="value"),
                    id="workflow-info"
                ),
                self.log_viewer_widget,
                Horizontal(
                    Button("Refresh", id="refresh-btn", variant="primary"),
                    Button("Export", id="export-btn", variant="success"),
                    id="log-controls"
                ),
                id="main-content"
            ),
            id="log-viewer-container"
        )
    
    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        # Load selected workflow from state
        selected_workflow = self.state_manager.get('ui.selected_workflow')
        if selected_workflow:
            self.selected_workflow_id = selected_workflow
            self.load_logs_for_workflow(selected_workflow)
    
    def watch_selected_workflow_id(self, old_value: str, new_value: str) -> None:
        """Called when the selected workflow ID changes."""
        if new_value:
            self.load_logs_for_workflow(new_value)
            # Update the static widget showing the selected workflow
            workflow_widget = self.query_one("#selected-workflow", Static)
            workflow_widget.update(new_value)
    
    def load_logs_for_workflow(self, workflow_id: str) -> None:
        """Load logs for the specified workflow."""
        try:
            # Get workflow data from state
            workflow_data = self.state_manager.get_workflow(workflow_id)
            if not workflow_data:
                self.logger.warning(f"Workflow {workflow_id} not found in state")
                return
            
            # In a real implementation, this would get actual log data
            # For now, we'll generate sample log data
            sample_logs = self._get_sample_logs(workflow_data, workflow_id)
            
            # Apply filters if any are set
            filtered_logs = self._apply_filters(sample_logs)
            
            # Update the log viewer widget
            self.log_viewer_widget.update_logs(filtered_logs)
            
        except Exception as e:
            self.logger.error(f"Error loading logs for workflow {workflow_id}: {str(e)}")
    
    def _get_sample_logs(self, workflow_data: Dict[str, Any], workflow_id: str) -> List[Dict[str, Any]]:
        """
        Get sample log entries for demonstration purposes.
        
        Args:
            workflow_data: Workflow data dictionary
            workflow_id: ID of the workflow
            
        Returns:
            List of sample log entries
        """
        # In a real implementation, this would read from actual log files
        # associated with the workflow
        sample_logs = [
            {
                'timestamp': '2023-10-01 10:01:01',
                'level': 'INFO',
                'task_id': 'task1',
                'status': 'started',
                'message': f'Workflow {workflow_id} started successfully'
            },
            {
                'timestamp': '2023-10-01 10:05:23',
                'level': 'INFO',
                'task_id': 'task2',
                'status': 'submitted',
                'message': 'Task task2 submitted to queue'
            },
            {
                'timestamp': '2023-10-01 10:10:45',
                'level': 'ERROR',
                'task_id': 'task3',
                'status': 'failed',
                'message': 'Task task3 failed with exit code 1'
            },
            {
                'timestamp': '2023-10-01 10:15:12',
                'level': 'WARNING',
                'task_id': 'task4',
                'status': 'running',
                'message': 'Resource usage high for task4'
            },
            {
                'timestamp': '2023-10-01 10:20:33',
                'level': 'INFO',
                'task_id': 'task5',
                'status': 'succeeded',
                'message': 'Task task5 completed successfully'
            },
            {
                'timestamp': '2023-10-01 10:25:15',
                'level': 'DEBUG',
                'task_id': 'task6',
                'status': 'running',
                'message': 'Debug: Processing intermediate step for task6'
            },
            {
                'timestamp': '2023-10-01 10:30:02',
                'level': 'INFO',
                'task_id': 'task7',
                'status': 'submitted',
                'message': 'Task task7 queued for execution'
            },
            {
                'timestamp': '2023-10-01 10:35:40',
                'level': 'ERROR',
                'task_id': 'task8',
                'status': 'failed',
                'message': 'Task task8 exceeded memory limit'
            }
        ]
        
        return sample_logs
    
    def _apply_filters(self, logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply current filters to the log entries.
        
        Args:
            logs: List of log entries to filter
            
        Returns:
            Filtered list of log entries
        """
        filtered_logs = []
        
        for log in logs:
            include = True
            
            if self.filters['level'] and self.filters['level'].upper() != log['level'].upper():
                include = False
            if self.filters['task_id'] and self.filters['task_id'].lower() not in log['task_id'].lower():
                include = False
            if self.filters['status'] and self.filters['status'].lower() not in log['status'].lower():
                include = False
            if self.filters['search_term'] and self.filters['search_term'].lower() not in log['message'].lower():
                include = False
            
            if include:
                filtered_logs.append(log)
        
        return filtered_logs
    
    def refresh(self) -> None:
        """Refresh the screen content."""
        if self.selected_workflow_id:
            self.load_logs_for_workflow(self.selected_workflow_id)
    
    def set_filter(self, filter_type: str, value: Optional[str]) -> bool:
        """
        Set a filter for log viewing.
        
        Args:
            filter_type: Type of filter ('level', 'task_id', 'status', 'search_term')
            value: Value to filter by (None to clear filter)
            
        Returns:
            True if filter was set successfully
        """
        if filter_type in self.filters:
            self.filters[filter_type] = value
            self.logger.info(f"Set filter {filter_type} to {value}")
            
            # Refresh logs with new filter
            if self.selected_workflow_id:
                self.load_logs_for_workflow(self.selected_workflow_id)
            return True
        else:
            self.logger.warning(f"Invalid filter type: {filter_type}")
            return False
    
    def clear_filters(self) -> bool:
        """Clear all log filters."""
        for key in self.filters:
            self.filters[key] = None
        self.logger.info("Cleared all filters")
        
        # Refresh logs without filters
        if self.selected_workflow_id:
            self.load_logs_for_workflow(self.selected_workflow_id)
        return True
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "refresh-btn":
            self.refresh()
        elif event.button.id == "export-btn":
            self.export_logs()
    
    def export_logs(self) -> None:
        """Export logs to a file."""
        # In a real implementation, this would prompt for a file path
        # For now, we'll just log that the export was requested
        self.logger.info(f"Export logs requested for workflow: {self.selected_workflow_id}")
        
        # Update state to indicate export is in progress
        self.state_manager.set('ui.export_in_progress', True)
        
        # Simulate export process
        # In a real implementation, this would actually write to a file
        self.logger.info("Logs exported successfully")
        self.state_manager.set('ui.export_in_progress', False)
    
    class LogEntrySelected(Message):
        """Message sent when a log entry is selected."""
        
        def __init__(self, log_entry: Dict[str, Any]) -> None:
            super().__init__()
            self.log_entry = log_entry