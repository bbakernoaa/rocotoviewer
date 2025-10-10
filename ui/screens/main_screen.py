"""
Main screen module for RocotoViewer Textual UI.

This module provides the main screen interface for the application.
"""

from typing import Any, Dict, Optional
import logging

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, DataTable, Tree, Button
from textual.message import Message
from textual.reactive import reactive

from ...config.config import Config
from ...core.state_manager import StateManager
from ...core.log_processor import LogProcessor
from ...parsers.workflow_parser import WorkflowParser
from ..widgets.workflow_viewer import WorkflowViewer
from ..widgets.navigation_panel import NavigationPanel
from ..widgets.search_filter import SearchFilter


class MainScreen(Container):
    """
    Main screen interface for RocotoViewer.
    """
    
    # Reactive attributes
    workflows = reactive([])
    
    def __init__(self, config: Config, state_manager: StateManager, 
                 log_processor: LogProcessor, workflow_parser: WorkflowParser):
        """
        Initialize the main screen.
        
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
        self.workflow_viewer = WorkflowViewer(config, state_manager, log_processor, workflow_parser)
        
        # Load initial workflows
        self.refresh_workflows()
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the main screen."""
        yield Horizontal(
            Vertical(
                self.navigation_panel,
                self.search_filter,
                id="sidebar"
            ),
            Vertical(
                Static("Workflow Overview", classes="screen-title"),
                self.workflow_viewer,
                id="main-content"
            ),
            id="main-screen-container"
        )
    
    def on_mount(self) -> None:
        """Called when the screen is mounted."""
        # Start periodic refresh if needed
        pass
    
    def refresh_workflows(self) -> None:
        """Refresh the list of workflows from state manager."""
        try:
            workflows = self.state_manager.get_all_workflows()
            workflow_list = []
            
            for workflow_id, workflow_data in workflows.items():
                wf_info = workflow_data.get('data', {})
                
                workflow_list.append({
                    'id': workflow_id,
                    'name': wf_info.get('name', workflow_id),
                    'status': workflow_data.get('status', 'unknown'),
                    'task_count': len(wf_info.get('tasks', [])),
                    'last_updated': workflow_data.get('last_updated', 'N/A')
                })
            
            self.workflows = workflow_list
            self.workflow_viewer.update_workflows(workflow_list)
            
        except Exception as e:
            self.logger.error(f"Error refreshing workflows: {str(e)}")
    
    def refresh(self) -> None:
        """Refresh the screen content."""
        self.refresh_workflows()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "refresh-btn":
            self.refresh_workflows()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the workflow table."""
        # Update workflow viewer to show selected workflow
        selected_row_key = event.row_key.value
        if selected_row_key < len(self.workflows):
            selected_workflow = self.workflows[selected_row_key]
            self.workflow_viewer.select_workflow(selected_workflow['id'])
    
    class WorkflowSelected(Message):
        """Message sent when a workflow is selected."""
        
        def __init__(self, workflow_id: str) -> None:
            super().__init__()
            self.workflow_id = workflow_id


class WorkflowOverviewTable(DataTable):
    """Table widget to display workflow overview."""
    
    def __init__(self):
        super().__init__()
        self.cursor_type = "row"
        
        # Add columns
        self.add_column("ID", key="id")
        self.add_column("Name", key="name")
        self.add_column("Status", key="status")
        self.add_column("Tasks", key="task_count")
        self.add_column("Last Updated", key="last_updated")
    
    def populate_table(self, workflows: list) -> None:
        """Populate the table with workflow data."""
        # Clear existing rows
        self.clear()
        
        # Add new rows
        for workflow in workflows:
            self.add_row(
                workflow['id'],
                workflow['name'],
                workflow['status'],
                str(workflow['task_count']),
                str(workflow['last_updated'])
            )