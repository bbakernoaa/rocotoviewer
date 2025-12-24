"""
Main Textual application UI for RocotoViewer.

This module provides the main UI application using Textual for terminal UI.
"""

from typing import Optional
import logging

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Tree, DataTable
from textual.binding import Binding

from ..config.config import Config
from ..core.state_manager import StateManager
from ..core.log_processor import StreamingLogProcessor
from ..parsers.workflow_parser import WorkflowParser
from .screens.main_screen import MainScreen
from .screens.log_viewer_screen import LogViewerScreen
from .themes.default import DefaultTheme


class RocotoViewerApp(App):
    """
    Main Textual application for RocotoViewer.
    """
    
    TITLE = "RocotoViewer - Workflow Management System Viewer"
    SUB_TITLE = "Real-time monitoring and visualization of Rocoto workflows"
    
    CSS_PATH = "app.tcss"
    
    BINDINGS = [
        Binding("m", "switch_to_main", "Main View"),
        Binding("l", "switch_to_log_viewer", "Log Viewer"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+d", "quit", "Quit"),
    ]
    
    def __init__(self, config: Config, state_manager: StateManager, 
                 log_processor: StreamingLogProcessor, workflow_parser: WorkflowParser):
        """
        Initialize the application.
        
        Args:
            config: Application configuration
            state_manager: State manager instance
            log_processor: Log processor instance
            workflow_parser: Workflow parser instance
        """
        self.config = config
        self.state_manager = state_manager
        self.log_processor = log_processor
        self.workflow_parser = workflow_parser
        self.logger = logging.getLogger(__name__)
        
        # Current screen
        self.current_screen = "main"
        
        # Create screen instances
        self.main_screen = MainScreen(config, state_manager, log_processor, workflow_parser)
        self.log_viewer_screen = LogViewerScreen(config, state_manager, log_processor, workflow_parser)

        super().__init__()
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Container(
            Horizontal(
                Vertical(
                    Static("Navigation", classes="nav-title"),
                    Static("• Main View (M)", classes="nav-item"),
                    Static("• Log Viewer (L)", classes="nav-item"),
                    Static("• Settings", classes="nav-item"),
                    classes="sidebar"
                ),
                Vertical(
                    self.main_screen,
                    id="main-content"
                ),
                classes="main-container"
            )
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Called when app is mounted."""
        # Set initial content to main screen
        self.query_one("#main-content").mount(self.main_screen)
        self.refresh_ui()
    
    def action_switch_to_main(self) -> None:
        """Switch to main screen."""
        self.current_screen = "main"
        content_container = self.query_one("#main-content", Container)
        content_container.remove_children()
        content_container.mount(self.main_screen)
        self.refresh_ui()
    
    def action_switch_to_log_viewer(self) -> None:
        """Switch to log viewer screen."""
        self.current_screen = "log_viewer"
        content_container = self.query_one("#main-content", Container)
        content_container.remove_children()
        content_container.mount(self.log_viewer_screen)
        self.refresh_ui()
    
    def action_refresh(self) -> None:
        """Refresh the current screen."""
        if self.current_screen == "main":
            self.main_screen.refresh()
        elif self.current_screen == "log_viewer":
            self.log_viewer_screen.refresh()
    
    def refresh_ui(self) -> None:
        """Refresh the entire UI."""
        self._log("UI refreshed")
    
    def _log(self, message: str) -> None:
        """Log a message to the status bar or console."""
        self.logger.info(message)
    
    def watch_current_screen(self, old_screen: str, new_screen: str) -> None:
        """Called when the current screen changes."""
        self._log(f"Switched from {old_screen} to {new_screen}")
    
    def refresh(self, *, repaint: bool = True, layout: bool = False, recompose: bool = True) -> 'RocotoViewerApp':
        """Refresh the application display."""
        self.action_refresh()
        return self
    
    def load_workflow(self, workflow_path: str) -> None:
        """
        Load a workflow into the application.
        
        Args:
            workflow_path: Path to workflow file
        """
        try:
            workflow_data = self.workflow_parser.parse(workflow_path)
            workflow_id = workflow_data.get('id', 'unknown')
            
            # Update state with new workflow
            self.state_manager.update_workflow(workflow_id, workflow_data)
            
            self.logger.info(f"Loaded workflow: {workflow_id}")
        except Exception as e:
            self.logger.error(f"Error loading workflow {workflow_path}: {str(e)}")
    
    def get_current_workflows(self):
        """Get current workflows from state manager."""
        return self.state_manager.get_all_workflows()