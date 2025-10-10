"""
Navigation panel widget module for RocotoViewer Textual UI.

This module provides an enhanced navigation panel for switching between different views
with additional workflow controls.
"""

from typing import Any, Dict, List, Optional, Callable
import logging

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, Grid
from textual.widgets import Static, Button, Tree, Input, Label
from textual.reactive import reactive
from textual.message import Message
from textual.events import Click

from ...config.config import Config
from ...core.state_manager import StateManager
from ...core.log_processor import LogProcessor
from ...parsers.workflow_parser import WorkflowParser
from ...core.event_bus import get_event_bus, WorkflowEvent


class NavigationPanel(Container):
    """
    Enhanced widget for navigation between different views in the UI with workflow controls.
    """
    
    # Reactive attributes
    current_view = reactive("main")
    selected_workflow_id = reactive("")
    
    def __init__(self, config: Config, state_manager: StateManager, 
                 log_processor: LogProcessor, workflow_parser: WorkflowParser):
        """
        Initialize the navigation panel widget.
        
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
        self.event_bus = get_event_bus()
        
        # Navigation items
        self.navigation_items = [
            {'id': 'main', 'label': '🏠 Main View', 'shortcut': 'M'},
            {'id': 'workflows', 'label': '🔄 Workflows', 'shortcut': 'W'},
            {'id': 'logs', 'label': '📝 Log Viewer', 'shortcut': 'L'},
            {'id': 'settings', 'label': '⚙️ Settings', 'shortcut': 'S'},
            {'id': 'help', 'label': '❓ Help', 'shortcut': 'H'}
        ]
        
        # Callbacks for navigation actions
        self.navigation_callbacks: Dict[str, Callable] = {}
        
        # Workflow control buttons
        self.refresh_button = Button("🔄 Refresh", id="refresh-workflows", variant="primary")
        self.expand_all_button = Button("Expand All", id="expand-all", variant="default")
        self.collapse_all_button = Button("Collapse All", id="collapse-all", variant="default")
        self.search_input = Input(placeholder="Search workflows...", id="search-input")
        self.workflow_tree = Tree("Workflows", id="nav-workflow-tree")
        
        # Initialize workflow controls
        self.workflow_controls = Vertical(
            Label("Workflow Controls", id="workflow-controls-label"),
            self.refresh_button,
            Horizontal(
                self.expand_all_button,
                self.collapse_all_button,
                id="expand-collapse-container"
            ),
            self.search_input,
            id="workflow-controls"
        )
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the navigation panel."""
        yield Vertical(
            Static("Navigation", classes="nav-title"),
            *[Button(item['label'], id=f"nav-{item['id']}", variant="primary") 
              for item in self.navigation_items],
            self.workflow_controls,
            self.workflow_tree,
            id="navigation-container"
        )
    
    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        # Load current view from state
        current_view = self.state_manager.get('ui.current_view', 'main')
        self.current_view = current_view
        self._update_button_states()
        
        # Load workflows into tree
        self._update_workflow_tree()
        
        # Subscribe to workflow events
        self.event_bus.subscribe_to_type(WorkflowEvent, self._on_workflow_event)
    
    def _on_workflow_event(self, event: WorkflowEvent):
        """Handle workflow state update events."""
        self.logger.debug(f"Navigation panel received workflow event: {event.type}")
        if event.type in ["workflow_updated", "workflow_added", "workflow_removed"]:
            self.call_later(self._update_workflow_tree)
    
    def handle_navigation(self, nav_id: str) -> bool:
        """
        Handle navigation to a specific view.
        
        Args:
            nav_id: ID of the navigation target
            
        Returns:
            True if navigation was handled successfully
        """
        try:
            # Update the current view in state
            self.state_manager.set('ui.current_view', nav_id)
            self.current_view = nav_id
            
            # Execute any registered callback for this navigation
            if nav_id in self.navigation_callbacks:
                callback = self.navigation_callbacks[nav_id]
                callback(nav_id)
            
            self.logger.info(f"Navigated to view: {nav_id}")
            self._update_button_states()
            return True
        except Exception as e:
            self.logger.error(f"Error handling navigation to {nav_id}: {str(e)}")
            return False
    
    def register_navigation_callback(self, nav_id: str, callback: Callable[[str], None]):
        """
        Register a callback for when a specific navigation item is selected.
        
        Args:
            nav_id: ID of the navigation item
            callback: Function to call when navigation occurs
        """
        self.navigation_callbacks[nav_id] = callback
    
    def get_shortcut_map(self) -> Dict[str, str]:
        """
        Get a mapping of shortcuts to navigation IDs.
        
        Returns:
            Dictionary mapping shortcuts to navigation IDs
        """
        return {item['shortcut'].lower(): item['id'] for item in self.navigation_items}
    
    def get_current_view(self) -> str:
        """
        Get the current view from state.
        
        Returns:
            Current view ID
        """
        return self.state_manager.get('ui.current_view', 'main')
    
    def set_current_view(self, view_id: str) -> bool:
        """
        Set the current view in state.
        
        Args:
            view_id: ID of the view to set as current
            
        Returns:
            True if view was set successfully
        """
        try:
            self.state_manager.set('ui.current_view', view_id)
            self.current_view = view_id
            self._update_button_states()
            return True
        except Exception as e:
            self.logger.error(f"Error setting current view to {view_id}: {str(e)}")
            return False
    
    def watch_current_view(self, old_value: str, new_value: str) -> None:
        """Called when the current view changes."""
        self._update_button_states()
    
    def _update_button_states(self) -> None:
        """Update the visual state of navigation buttons."""
        # Update button styles based on current view
        for item in self.navigation_items:
            button = self.query_one(f"#nav-{item['id']}", Button)
            if item['id'] == self.current_view:
                button.variant = "success"
                button.label = f"→ {item['label']}"
            else:
                button.variant = "primary"
                # Remove the arrow if it was there
                if button.label.startswith("→ "):
                    button.label = item['label']
    
    def get_available_workflows(self) -> List[Dict[str, Any]]:
        """
        Get a list of available workflows for navigation purposes.
        
        Returns:
            List of workflow dictionaries
        """
        workflows = self.state_manager.get_all_workflows()
        workflow_list = []
        
        for wf_id, wf_data in workflows.items():
            wf_info = wf_data.get('data', {})
            workflow_list.append({
                'id': wf_id,
                'name': wf_info.get('name', wf_id),
                'status': wf_data.get('status', 'unknown'),
                'task_count': len(wf_info.get('tasks', [])),
                'last_updated': wf_data.get('last_updated', 'N/A')
            })
        
        return workflow_list
    
    def _update_workflow_tree(self) -> None:
        """Update the workflow tree with current workflows."""
        # Get workflows from state
        workflows = self.get_available_workflows()
        
        # Clear the tree
        self.workflow_tree.clear()
        
        # Add workflows to the tree
        for workflow in workflows:
            status_symbol = self._get_status_symbol(workflow['status'])
            workflow_node = self.workflow_tree.root.add(
                f"{status_symbol} {workflow['name']} ({workflow['task_count']} tasks)",
                data=workflow['id']
            )
            
            # Add task count as child
            if workflow['task_count'] > 0:
                task_summary = self._get_task_summary(workflow['id'])
                workflow_node.add(task_summary)
    
    def _get_status_symbol(self, status: str) -> str:
        """Get a symbol representing the workflow status."""
        status_lower = status.lower()
        if status_lower in ['success', 'succeeded', 'completed']:
            return "✅"
        elif status_lower in ['failed', 'error']:
            return "❌"
        elif status_lower in ['running', 'active', 'r']:
            return "🏃"
        elif status_lower in ['queued', 'pending', 'q']:
            return "⏳"
        elif status_lower in ['held', 'h']:
            return "⏸️"
        else:
            return "❓"
    
    def _get_task_summary(self, workflow_id: str) -> str:
        """Get a task summary for the specified workflow."""
        workflow_data = self.state_manager.get_workflow(workflow_id)
        if not workflow_data or 'data' not in workflow_data or 'tasks' not in workflow_data['data']:
            return "No tasks"
        
        tasks = workflow_data['data']['tasks']
        total = len(tasks)
        
        # Count task statuses
        status_counts = {}
        for task in tasks:
            status = task.get('status', 'unknown').lower()
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Format summary
        summary_parts = []
        if 'success' in status_counts:
            summary_parts.append(f"✅ {status_counts['success']}")
        if 'failed' in status_counts:
            summary_parts.append(f"❌ {status_counts['failed']}")
        if 'running' in status_counts:
            summary_parts.append(f"🏃 {status_counts['running']}")
        if 'queued' in status_counts:
            summary_parts.append(f"⏳ {status_counts['queued']}")
        
        if summary_parts:
            return f"Tasks: {' '.join(summary_parts)} ({total} total)"
        else:
            return f"Tasks: {total} total"
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        button_id = event.button.id
        if button_id and button_id.startswith("nav-"):
            nav_id = button_id[4:]  # Remove "nav-" prefix
            self.handle_navigation(nav_id)
        elif button_id == "refresh-workflows":
            self._refresh_workflows()
        elif button_id == "expand-all":
            self.workflow_tree.root.expand_all()
        elif button_id == "collapse-all":
            self.workflow_tree.root.collapse_all()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission."""
        search_term = event.value.lower()
        self._filter_workflows(search_term)
    
    def _filter_workflows(self, search_term: str) -> None:
        """Filter workflows based on search term."""
        # This would implement filtering logic in a real application
        # For now, just log the search term
        self.logger.debug(f"Filtering workflows with search term: {search_term}")
    
    def _refresh_workflows(self) -> None:
        """Refresh the workflow list."""
        self.logger.info("Refreshing workflows")
        # Trigger a refresh of workflow data
        # In a real implementation, this would re-parse workflow files
        self._update_workflow_tree()
        
        # Emit refresh event
        self.event_bus.publish(WorkflowEvent(
            type="workflows_refreshed",
            data={"timestamp": self._get_current_timestamp()},
            source="NavigationPanel"
        ))
    
    def _get_current_timestamp(self) -> str:
        """Get the current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection in the workflow tree."""
        if event.node.data:  # If the node has data (workflow ID)
            workflow_id = event.node.data
            self.selected_workflow_id = workflow_id
            
            # Emit workflow selected event
            self.post_message(self.WorkflowSelected(workflow_id))
    
    class NavigationRequested(Message):
        """Message sent when navigation is requested."""
        
        def __init__(self, target_view: str) -> None:
            super().__init__()
            self.target_view = target_view
    
    class WorkflowSelected(Message):
        """Message sent when a workflow is selected from the navigation panel."""
        
        def __init__(self, workflow_id: str) -> None:
            super().__init__()
            self.workflow_id = workflow_id


class WorkflowNavigationTree(Tree):
    """Enhanced tree widget for navigating workflows with status visualization."""
    
    def __init__(self):
        super().__init__("Workflows")
    
    def populate_tree(self, workflows: List[Dict[str, Any]]) -> None:
        """Populate the tree with workflow data."""
        self.clear()
        
        for workflow in workflows:
            status_symbol = self._get_status_symbol(workflow['status'])
            workflow_node = self.root.add(
                f"{status_symbol} {workflow['name']} ({workflow['status']})",
                data=workflow['id']
            )
            
            # Add tasks as children
            if workflow['task_count'] > 0:
                task_summary = f"Tasks ({workflow['task_count']})"
                workflow_node.add(task_summary)
    
    def _get_status_symbol(self, status: str) -> str:
        """Get a symbol representing the workflow status."""
        status_lower = status.lower()
        if status_lower in ['success', 'succeeded', 'completed']:
            return "✅"
        elif status_lower in ['failed', 'error']:
            return "❌"
        elif status_lower in ['running', 'active', 'r']:
            return "🏃"
        elif status_lower in ['queued', 'pending', 'q']:
            return "⏳"
        elif status_lower in ['held', 'h']:
            return "⏸️"
        else:
            return "❓"