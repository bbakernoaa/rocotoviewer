"""
Search filter widget module for RocotoViewer Textual UI.

This module provides a widget for searching and filtering data in the UI.
"""

from typing import Any, Dict, List, Optional, Callable
import logging
import re

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Input, Button, Select, Checkbox
from textual.reactive import reactive
from textual.message import Message

from ...config.config import Config
from ...core.state_manager import StateManager
from ...core.log_processor import LogProcessor
from ...parsers.workflow_parser import WorkflowParser


class SearchFilter(Container):
    """
    Widget for searching and filtering data in the UI.
    """
    
    # Reactive attributes
    search_term = reactive("")
    workflow_filter = reactive("")
    task_status_filter = reactive("")
    log_level_filter = reactive("")
    
    def __init__(self, config: Config, state_manager: StateManager, 
                 log_processor: LogProcessor, workflow_parser: WorkflowParser):
        """
        Initialize the search filter widget.
        
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
        
        # Current filter state
        self.filters = {
            'search_term': '',
            'workflow_id': None,
            'task_status': None,
            'log_level': None,
            'date_range': None
        }
        
        # Callbacks for filter changes
        self.filter_callbacks: List[Callable] = []
        
        # Initialize widgets
        self.search_input = Input(placeholder="Search...", id="search-input")
        self.workflow_select = Select(
            [(wf_id, wf_id) for wf_id in self._get_workflow_ids()],
            prompt="All Workflows",
            id="workflow-select"
        )
        self.status_select = Select(
            [("All", "All"), ("running", "Running"), ("succeeded", "Succeeded"), 
             ("failed", "Failed"), ("submitted", "Submitted")],
            prompt="All Statuses",
            id="status-select"
        )
        self.level_select = Select(
            [("All", "All"), ("INFO", "INFO"), ("WARNING", "WARNING"), 
             ("ERROR", "ERROR"), ("DEBUG", "DEBUG")],
            prompt="All Levels",
            id="level-select"
        )
        self.clear_button = Button("Clear Filters", variant="warning", id="clear-filters-btn")
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the search filter."""
        yield Vertical(
            Horizontal(
                self.search_input,
                id="search-row"
            ),
            Horizontal(
                Static("Workflow:", classes="filter-label"),
                self.workflow_select,
                id="workflow-filter-row"
            ),
            Horizontal(
                Static("Status:", classes="filter-label"),
                self.status_select,
                id="status-filter-row"
            ),
            Horizontal(
                Static("Level:", classes="filter-label"),
                self.level_select,
                id="level-filter-row"
            ),
            Horizontal(
                self.clear_button,
                id="filter-actions"
            ),
            id="search-filter-container"
        )
    
    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        # Update workflow options
        self._update_workflow_options()
    
    def _get_workflow_ids(self) -> List[str]:
        """Get a list of available workflow IDs."""
        workflows = self.state_manager.get_all_workflows()
        return list(workflows.keys())
    
    def _update_workflow_options(self) -> None:
        """Update the workflow selection options."""
        workflow_ids = self._get_workflow_ids()
        options = [(wf_id, wf_id) for wf_id in workflow_ids]
        options.insert(0, ("", "All Workflows"))  # Add "All" option
        self.workflow_select.set_options(options)
    
    def set_filter(self, filter_type: str, value: Any) -> bool:
        """
        Set a filter value.
        
        Args:
            filter_type: Type of filter to set
            value: Value to set for the filter
            
        Returns:
            True if filter was set successfully
        """
        if filter_type not in self.filters:
            self.logger.warning(f"Invalid filter type: {filter_type}")
            return False
        
        old_value = self.filters[filter_type]
        self.filters[filter_type] = value
        
        self.logger.info(f"Filter {filter_type} changed from {old_value} to {value}")
        
        # Execute callbacks
        self._execute_callbacks(filter_type, old_value, value)
        
        # Update reactive attributes
        if filter_type == 'search_term':
            self.search_term = value
        elif filter_type == 'workflow_id':
            self.workflow_filter = value
        elif filter_type == 'task_status':
            self.task_status_filter = value
        elif filter_type == 'log_level':
            self.log_level_filter = value
        
        return True
    
    def get_filter(self, filter_type: str) -> Any:
        """
        Get the value of a filter.
        
        Args:
            filter_type: Type of filter to get
            
        Returns:
            Current value of the filter
        """
        return self.filters.get(filter_type)
    
    def clear_filter(self, filter_type: str) -> bool:
        """
        Clear a specific filter.
        
        Args:
            filter_type: Type of filter to clear
            
        Returns:
            True if filter was cleared successfully
        """
        if filter_type not in self.filters:
            return False
        
        old_value = self.filters[filter_type]
        if filter_type == 'search_term':
            self.filters[filter_type] = ''
        else:
            self.filters[filter_type] = None
        
        self.logger.info(f"Cleared filter {filter_type} (was {old_value})")
        
        # Execute callbacks
        self._execute_callbacks(filter_type, old_value, self.filters[filter_type])
        
        return True
    
    def clear_all_filters(self) -> bool:
        """
        Clear all filters.
        
        Returns:
            True if all filters were cleared successfully
        """
        old_filters = self.filters.copy()
        
        for key in self.filters:
            if key == 'search_term':
                self.filters[key] = ''
            else:
                self.filters[key] = None
        
        self.logger.info("Cleared all filters")
        
        # Execute callbacks for each filter that changed
        for key, old_value in old_filters.items():
            if old_value != self.filters[key]:
                self._execute_callbacks(key, old_value, self.filters[key])
        
        # Reset UI elements
        self.search_input.value = ""
        self.workflow_select.value = ""
        self.status_select.value = ""
        self.level_select.value = ""
        
        return True
    
    def search_workflows(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Search through workflows using the search term.
        
        Args:
            search_term: Term to search for
            
        Returns:
            List of matching workflow dictionaries
        """
        all_workflows = self.state_manager.get_all_workflows()
        matching_workflows = []
        
        search_lower = search_term.lower()
        
        for wf_id, wf_data in all_workflows.items():
            wf_info = wf_data.get('data', {})
            
            # Check if search term matches workflow ID, name, or description
            if (search_lower in wf_id.lower() or 
                search_lower in wf_info.get('name', '').lower() or
                search_lower in wf_info.get('description', '').lower()):
                
                matching_workflows.append({
                    'id': wf_id,
                    'name': wf_info.get('name', wf_id),
                    'description': wf_info.get('description', ''),
                    'status': wf_data.get('status', 'unknown'),
                    'source': wf_info.get('source', 'N/A')
                })
        
        return matching_workflows
    
    def search_tasks(self, workflow_id: str, search_term: str) -> List[Dict[str, Any]]:
        """
        Search through tasks in a specific workflow.
        
        Args:
            workflow_id: ID of workflow to search in
            search_term: Term to search for
            
        Returns:
            List of matching task dictionaries
        """
        workflow_data = self.state_manager.get_workflow(workflow_id)
        if not workflow_data:
            return []
        
        wf_info = workflow_data.get('data', {})
        tasks = wf_info.get('tasks', [])
        
        search_lower = search_term.lower()
        matching_tasks = []
        
        for task in tasks:
            task_id = task.get('id', '')
            task_attrs = task.get('attributes', {})
            
            # Check if search term matches task ID or any attributes
            matches = (search_lower in task_id.lower() or
                      any(search_lower in str(v).lower() for v in task_attrs.values()))
            
            if matches:
                matching_tasks.append(task)
        
        return matching_tasks
    
    def filter_logs(self, logs: List[Dict[str, Any]], **filters) -> List[Dict[str, Any]]:
        """
        Apply filters to a list of log entries.
        
        Args:
            logs: List of log entries to filter
            **filters: Filter parameters
            
        Returns:
            Filtered list of log entries
        """
        filtered_logs = logs
        
        # Apply search term filter
        search_term = filters.get('search_term') or self.filters['search_term']
        if search_term:
            search_lower = search_term.lower()
            filtered_logs = [
                log for log in filtered_logs
                if (search_lower in log.get('message', '').lower() or
                    search_lower in log.get('task_id', '').lower())
            ]
        
        # Apply log level filter
        log_level = filters.get('log_level') or self.filters['log_level']
        if log_level:
            filtered_logs = [
                log for log in filtered_logs
                if log.get('level', '').lower() == log_level.lower()
            ]
        
        # Apply task status filter
        task_status = filters.get('task_status') or self.filters['task_status']
        if task_status:
            filtered_logs = [
                log for log in filtered_logs
                if task_status.lower() in (log.get('status') or '').lower()
            ]
        
        return filtered_logs
    
    def register_filter_callback(self, callback: Callable[[str, Any, Any], None]):
        """
        Register a callback for when filters change.
        
        Args:
            callback: Function to call when any filter changes
                    Function signature: callback(filter_type, old_value, new_value)
        """
        self.filter_callbacks.append(callback)
    
    def _execute_callbacks(self, filter_type: str, old_value: Any, new_value: Any):
        """
        Execute registered callbacks for filter changes.
        
        Args:
            filter_type: Type of filter that changed
            old_value: Previous value of the filter
            new_value: New value of the filter
        """
        for callback in self.filter_callbacks:
            try:
                callback(filter_type, old_value, new_value)
            except Exception as e:
                self.logger.error(f"Error in filter callback: {str(e)}")
    
    def get_active_filters(self) -> Dict[str, Any]:
        """
        Get a dictionary of currently active filters.
        
        Returns:
            Dictionary of active filters
        """
        active = {}
        for key, value in self.filters.items():
            if value:  # Consider empty strings and None as inactive
                active[key] = value
        return active
    
    def get_filter_summary(self) -> str:
        """
        Get a text summary of active filters.
        
        Returns:
            Summary of active filters as text
        """
        active_filters = self.get_active_filters()
        
        if not active_filters:
            return "No active filters"
        
        summary_parts = []
        for key, value in active_filters.items():
            key_name = key.replace('_', ' ').title()
            summary_parts.append(f"{key_name}: {value}")
        
        return ", ".join(summary_parts)
    
    def watch_search_term(self, old_value: str, new_value: str) -> None:
        """Called when the search term changes."""
        self.filters['search_term'] = new_value
        self._execute_callbacks('search_term', old_value, new_value)
    
    def watch_workflow_filter(self, old_value: str, new_value: str) -> None:
        """Called when the workflow filter changes."""
        self.filters['workflow_id'] = new_value if new_value else None
        self._execute_callbacks('workflow_id', old_value, new_value)
    
    def watch_task_status_filter(self, old_value: str, new_value: str) -> None:
        """Called when the task status filter changes."""
        self.filters['task_status'] = new_value if new_value else None
        self._execute_callbacks('task_status', old_value, new_value)
    
    def watch_log_level_filter(self, old_value: str, new_value: str) -> None:
        """Called when the log level filter changes."""
        self.filters['log_level'] = new_value if new_value else None
        self._execute_callbacks('log_level', old_value, new_value)
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self.search_term = event.value
    
    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle selection changes."""
        if event.select.id == "workflow-select":
            self.workflow_filter = event.value
        elif event.select.id == "status-select":
            self.task_status_filter = event.value
        elif event.select.id == "level-select":
            self.log_level_filter = event.value
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "clear-filters-btn":
            self.clear_all_filters()
    
    class FilterChanged(Message):
        """Message sent when a filter is changed."""
        
        def __init__(self, filter_type: str, old_value: Any, new_value: Any) -> None:
            super().__init__()
            self.filter_type = filter_type
            self.old_value = old_value
            self.new_value = new_value
    
    class SearchRequested(Message):
        """Message sent when a search is requested."""
        
        def __init__(self, search_term: str) -> None:
            super().__init__()
            self.search_term = search_term