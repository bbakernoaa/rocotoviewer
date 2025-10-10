"""
UI tests for RocotoViewer.

This module provides tests for the UI components.
"""

import pytest
from unittest.mock import Mock, MagicMock

from rocotoviewer.ui.app import RocotoViewerApp
from rocotoviewer.ui.screens.main_screen import MainScreen
from rocotoviewer.ui.screens.log_viewer_screen import LogViewerScreen
from rocotoviewer.ui.widgets.workflow_viewer import WorkflowViewer
from rocotoviewer.ui.widgets.log_viewer import LogViewer
from rocotoviewer.ui.widgets.navigation_panel import NavigationPanel
from rocotoviewer.ui.widgets.search_filter import SearchFilter
from rocotoviewer.ui.themes.default import DefaultTheme
from rocotoviewer.config.config import Config
from rocotoviewer.core.state_manager import StateManager
from rocotoviewer.core.log_processor import LogProcessor
from rocotoviewer.parsers.workflow_parser import WorkflowParser


def test_ui_components_can_be_imported():
    """Test that all UI components can be imported."""
    assert RocotoViewerApp is not None
    assert MainScreen is not None
    assert LogViewerScreen is not None
    assert WorkflowViewer is not None
    assert LogViewer is not None
    assert NavigationPanel is not None
    assert SearchFilter is not None
    assert DefaultTheme is not None


def test_rocoto_viewer_app_creation():
    """Test that RocotoViewerApp can be created with mock dependencies."""
    # Create mock dependencies
    mock_config = Mock(spec=Config)
    mock_config.display = Mock()
    mock_config.display.max_log_lines = 1000
    
    mock_state_manager = Mock(spec=StateManager)
    mock_state_manager.get_all_workflows.return_value = {}
    mock_state_manager.get_workflow.return_value = {}
    mock_state_manager.get.return_value = "main"
    
    mock_log_processor = Mock(spec=LogProcessor)
    mock_workflow_parser = Mock(spec=WorkflowParser)
    
    # Create the app
    app = RocotoViewerApp(mock_config, mock_state_manager, mock_log_processor, mock_workflow_parser)
    
    # Verify the app was created
    assert app is not None
    assert app.config == mock_config
    assert app.state_manager == mock_state_manager
    assert app.log_processor == mock_log_processor
    assert app.workflow_parser == mock_workflow_parser


def test_main_screen_creation():
    """Test that MainScreen can be created with mock dependencies."""
    # Create mock dependencies
    mock_config = Mock(spec=Config)
    mock_config.display = Mock()
    mock_config.display.max_log_lines = 1000
    
    mock_state_manager = Mock(spec=StateManager)
    mock_state_manager.get_all_workflows.return_value = {}
    mock_state_manager.get_workflow.return_value = {}
    mock_state_manager.get.return_value = "main"
    
    mock_log_processor = Mock(spec=LogProcessor)
    mock_workflow_parser = Mock(spec=WorkflowParser)
    
    # Create the screen
    screen = MainScreen(mock_config, mock_state_manager, mock_log_processor, mock_workflow_parser)
    
    # Verify the screen was created
    assert screen is not None
    assert screen.config == mock_config
    assert screen.state_manager == mock_state_manager
    assert screen.log_processor == mock_log_processor
    assert screen.workflow_parser == mock_workflow_parser


def test_log_viewer_screen_creation():
    """Test that LogViewerScreen can be created with mock dependencies."""
    # Create mock dependencies
    mock_config = Mock(spec=Config)
    mock_config.display = Mock()
    mock_config.display.max_log_lines = 1000
    
    mock_state_manager = Mock(spec=StateManager)
    mock_state_manager.get_all_workflows.return_value = {}
    mock_state_manager.get_workflow.return_value = {}
    mock_state_manager.get.return_value = "main"
    
    mock_log_processor = Mock(spec=LogProcessor)
    mock_workflow_parser = Mock(spec=WorkflowParser)
    
    # Create the screen
    screen = LogViewerScreen(mock_config, mock_state_manager, mock_log_processor, mock_workflow_parser)
    
    # Verify the screen was created
    assert screen is not None
    assert screen.config == mock_config
    assert screen.state_manager == mock_state_manager
    assert screen.log_processor == mock_log_processor
    assert screen.workflow_parser == mock_workflow_parser


def test_workflow_viewer_widget_creation():
    """Test that WorkflowViewer can be created with mock dependencies."""
    # Create mock dependencies
    mock_config = Mock(spec=Config)
    mock_config.display = Mock()
    mock_config.display.max_log_lines = 1000
    
    mock_state_manager = Mock(spec=StateManager)
    mock_state_manager.get_all_workflows.return_value = {}
    mock_state_manager.get_workflow.return_value = {}
    mock_state_manager.get.return_value = "main"
    
    mock_log_processor = Mock(spec=LogProcessor)
    mock_workflow_parser = Mock(spec=WorkflowParser)
    
    # Create the widget
    widget = WorkflowViewer(mock_config, mock_state_manager, mock_log_processor, mock_workflow_parser)
    
    # Verify the widget was created
    assert widget is not None
    assert widget.config == mock_config
    assert widget.state_manager == mock_state_manager
    assert widget.log_processor == mock_log_processor
    assert widget.workflow_parser == mock_workflow_parser


def test_log_viewer_widget_creation():
    """Test that LogViewer can be created with mock dependencies."""
    # Create mock dependencies
    mock_config = Mock(spec=Config)
    mock_config.display = Mock()
    mock_config.display.max_log_lines = 1000
    
    mock_state_manager = Mock(spec=StateManager)
    mock_state_manager.get_all_workflows.return_value = {}
    mock_state_manager.get_workflow.return_value = {}
    mock_state_manager.get.return_value = "main"
    
    mock_log_processor = Mock(spec=LogProcessor)
    mock_workflow_parser = Mock(spec=WorkflowParser)
    
    # Create the widget
    widget = LogViewer(mock_config, mock_state_manager, mock_log_processor, mock_workflow_parser)
    
    # Verify the widget was created
    assert widget is not None
    assert widget.config == mock_config
    assert widget.state_manager == mock_state_manager
    assert widget.log_processor == mock_log_processor
    assert widget.workflow_parser == mock_workflow_parser


def test_navigation_panel_widget_creation():
    """Test that NavigationPanel can be created with mock dependencies."""
    # Create mock dependencies
    mock_config = Mock(spec=Config)
    mock_config.display = Mock()
    mock_config.display.max_log_lines = 1000
    
    mock_state_manager = Mock(spec=StateManager)
    mock_state_manager.get_all_workflows.return_value = {}
    mock_state_manager.get_workflow.return_value = {}
    mock_state_manager.get.return_value = "main"
    
    mock_log_processor = Mock(spec=LogProcessor)
    mock_workflow_parser = Mock(spec=WorkflowParser)
    
    # Create the widget
    widget = NavigationPanel(mock_config, mock_state_manager, mock_log_processor, mock_workflow_parser)
    
    # Verify the widget was created
    assert widget is not None
    assert widget.config == mock_config
    assert widget.state_manager == mock_state_manager
    assert widget.log_processor == mock_log_processor
    assert widget.workflow_parser == mock_workflow_parser


def test_search_filter_widget_creation():
    """Test that SearchFilter can be created with mock dependencies."""
    # Create mock dependencies
    mock_config = Mock(spec=Config)
    mock_config.display = Mock()
    mock_config.display.max_log_lines = 1000
    
    mock_state_manager = Mock(spec=StateManager)
    mock_state_manager.get_all_workflows.return_value = {}
    mock_state_manager.get_workflow.return_value = {}
    mock_state_manager.get.return_value = "main"
    
    mock_log_processor = Mock(spec=LogProcessor)
    mock_workflow_parser = Mock(spec=WorkflowParser)
    
    # Create the widget
    widget = SearchFilter(mock_config, mock_state_manager, mock_log_processor, mock_workflow_parser)
    
    # Verify the widget was created
    assert widget is not None
    assert widget.config == mock_config
    assert widget.state_manager == mock_state_manager
    assert widget.log_processor == mock_log_processor
    assert widget.workflow_parser == mock_workflow_parser


def test_default_theme_creation():
    """Test that DefaultTheme can be created."""
    theme = DefaultTheme()
    
    # Verify the theme was created
    assert theme is not None
    assert theme.name == "rocotoviewer-default"
    assert theme.primary is not None


def test_theme_methods():
    """Test that theme methods work correctly."""
    theme = DefaultTheme()
    
    # Test color methods
    assert theme.get_color('primary') == theme.primary
    assert theme.get_color('invalid_color') == '#FFFFFF'  # Default
    
    # Test status color methods
    assert theme.get_status_color('success') == theme.success
    assert theme.get_status_color('error') == theme.error
    assert theme.get_status_color('warning') == theme.warning
    assert theme.get_status_color('unknown') == theme.text


if __name__ == "__main__":
    pytest.main([__file__])