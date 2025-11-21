"""
Workflow viewer widget module for RocotoViewer Textual UI.

This module provides an enhanced widget for displaying workflow information with
interactive visualization capabilities.
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, ScrollableContainer
from textual.widgets import Static, Tree, DataTable, Button, Label, ProgressBar, Input
from textual.reactive import reactive
from textual.message import Message
from textual.events import Click
from textual import work
from rich.text import Text
from textual.coordinate import Coordinate

from ...config.config import Config
from ...core.state_manager import StateManager
from ...core.log_processor import LogProcessor
from ...parsers.workflow_parser import WorkflowParser
from ...core.event_bus import WorkflowEvent, get_event_bus
from ...utils.formatting import FormattingUtils
from ...utils.status_visualization import StatusVisualization
from ...utils.dependency_visualization import DependencyVisualization
from ...utils.search_utils import SearchUtils
from ...utils.performance_utils import PerformanceOptimizer


class WorkflowViewer(Container):
    """
    Enhanced widget for displaying workflow information in the UI with interactive visualization.
    """
    
    # Reactive attributes
    selected_workflow_id = reactive("")
    workflows = reactive([])
    selected_task_id = reactive("")
    filter_state = reactive("")
    search_term = reactive("")
    
    def __init__(self, config: Config, state_manager: StateManager, 
                 log_processor: LogProcessor, workflow_parser: WorkflowParser):
        """
        Initialize the workflow viewer widget.
        
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
        
        # Register for workflow state updates
        self.event_bus.subscribe_to_type(WorkflowEvent, self._on_workflow_event)
        
        # Initialize widgets
        self.workflow_tree = Tree("Workflows", id="workflow-tree")
        self.task_table = DataTable(id="task-table")
        self.workflow_details = Static(id="workflow-details")
        self.progress_bar = ProgressBar(id="workflow-progress")
        self.status_summary = Static(id="status-summary")
        self.dependency_graph = Static(id="dependency-graph")
        
        # Initialize performance optimizer
        self.performance_optimizer = PerformanceOptimizer()
        
        # Initialize search and filter controls
        self.search_label = Static("🔍 Search: ", id="search-label")
        self.search_input = Input(placeholder="Enter search term...", id="search-input")
        self.filter_controls = Horizontal(
            Button("All", id="filter-all", variant="primary"),
            Button("Running", id="filter-running", variant="primary"),
            Button("Failed", id="filter-failed", variant="primary"),
            Button("Success", id="filter-success", variant="primary"),
            Button("Dependencies", id="filter-dependencies", variant="primary"),
            id="filter-controls"
        )
        
        # Advanced filtering options
        self.advanced_filter_controls = Horizontal(
            Button("Show Circular", id="show-circular", variant="warning"),
            Button("Upstream", id="filter-upstream", variant="default"),
            Button("Downstream", id="filter-downstream", variant="default"),
            id="advanced-filter-controls"
        )
        
        # Context menu state
        self.context_menu_visible = False
        self.context_menu = Static("", id="context-menu", classes="context-menu")
        
        # Keyboard navigation state
        self.task_table_row_index = 0
    
    def compose(self) -> ComposeResult:
        """Create child widgets for the workflow viewer."""
        yield Horizontal(
            ScrollableContainer(
                self.workflow_tree,
                id="workflow-tree-container"
            ),
            Vertical(
                Horizontal(
                    self.search_label,
                    self.search_input,
                    id="search-container"
                ),
                self.filter_controls,
                self.advanced_filter_controls,
                self.task_table,
                self.progress_bar,
                self.status_summary,
                self.workflow_details,
                self.dependency_graph,
                id="workflow-details-container"
            ),
            id="workflow-viewer-container"
        )
        yield self.context_menu
    
    def on_mount(self) -> None:
        """Called when the widget is mounted."""
        # Set up the task table
        self.task_table.add_column("ID", key="id")
        self.task_table.add_column("Status", key="status")
        self.task_table.add_column("Cycle", key="cycle")
        self.task_table.add_column("Start Time", key="start_time")
        self.task_table.add_column("End Time", key="end_time")
        self.task_table.add_column("Duration", key="duration")

        # Load initial workflows
        self.update_workflows()
        
        # Set up periodic refresh if configured
        if self.config.display.refresh_interval > 0:
            self.set_interval(self.config.display.refresh_interval, self.refresh)
        
        # Set up periodic refresh if configured
        if self.config.display.refresh_interval > 0:
            self.set_interval(self.config.display.refresh_interval, self.refresh_view)
    
    def _on_workflow_event(self, event: WorkflowEvent):
        """Handle workflow state update events."""
        self.logger.debug(f"Received workflow event: {event.type}, {event.data}")
        if event.type in ["workflow_updated", "workflow_state_changed"]:
            self.call_later(self.update_workflows)
    
    def update_workflows(self, workflows: Optional[List[Dict[str, Any]]] = None) -> None:
        """
        Update the workflow viewer with new workflow data.
        
        Args:
            workflows: Optional list of workflow data (if None, fetch from state)
        """
        if workflows is None:
            # Get workflows from state manager
            all_workflows = self.state_manager.get_all_workflows()
            workflows = []
            
            for workflow_id, workflow_data in all_workflows.items():
                wf_info = workflow_data.get('data', {})
                
                workflows.append({
                    'id': workflow_id,
                    'name': wf_info.get('name', workflow_id),
                    'status': workflow_data.get('status', 'unknown'),
                    'task_count': len(wf_info.get('tasks', [])),
                    'data': wf_info
                })
        
        self.workflows = workflows
        self._update_workflow_tree()
        if self.selected_workflow_id:
            self.select_workflow(self.selected_workflow_id)
    
    def _update_workflow_tree(self) -> None:
        """Update the workflow tree with current workflows."""
        # Clear the tree
        self.workflow_tree.clear()
        
        # Add workflows to the tree
        for workflow in self.workflows:
            # Format workflow name with status indicator
            status_text = self._get_status_text(workflow['status'])
            workflow_node = self.workflow_tree.root.add(
                f"{workflow['name']} {status_text}",
                data=workflow['id']
            )
            
            # Add tasks as children if expanded
            if 'data' in workflow and 'tasks' in workflow['data']:
                task_count = len(workflow['data']['tasks'])
                task_summary = self._get_task_summary(workflow['data']['tasks'])
                
                # Add task summary node
                summary_node = workflow_node.add(f"Tasks ({task_count}) - {task_summary}")
                
                # Add filtered tasks as children with performance optimization
                filtered_tasks = self._filter_tasks(workflow['data']['tasks'])
                optimized_tasks = self.performance_optimizer.get_paginated_tasks(filtered_tasks, page=1, page_size=20)
                
                for task in optimized_tasks:
                    task_id = task.get('id', 'unknown')
                    task_status = task.get('status', 'unknown')
                    status_text = self._get_status_text(task_status)
                    summary_node.add(f"{task_id} {status_text}")
                
                if len(filtered_tasks) > 20:
                    summary_node.add(f"... and {len(filtered_tasks) - 20} more")
    
    def _get_status_text(self, status: str) -> str:
        """Get formatted status text with color coding."""
        return StatusVisualization.format_status_text(status).markup
    
    def _get_task_summary(self, tasks: List[Dict[str, Any]]) -> str:
        """Get a summary of task statuses."""
        summary = FormattingUtils.format_task_summary(tasks)
        return f"S:{summary['success']} F:{summary['failed']} R:{summary['running']} Q:{summary['queued']}"
    
    def _filter_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter tasks based on current filter and search criteria."""
        filtered = tasks
        
        # Apply state filter
        if self.filter_state and self.filter_state not in ['dependencies', 'circular', 'upstream', 'downstream']:
            filtered = [t for t in filtered if t.get('status', '').lower() == self.filter_state.lower()]
        
        # Apply search filter using SearchUtils
        if self.search_term:
            filtered = SearchUtils.search_tasks(filtered, self.search_term)
        
        # Apply special filters
        if self.filter_state == 'dependencies':
            # Show only tasks that have dependencies
            filtered = [t for t in filtered if t.get('dependencies', [])]
        elif self.filter_state == 'circular':
            # Show tasks that are part of circular dependencies
            circular_deps = DependencyVisualization.find_circular_dependencies(tasks)
            circular_task_ids = set()
            for cycle in circular_deps:
                circular_task_ids.update(cycle)
            filtered = [t for t in filtered if t.get('id') in circular_task_ids]
        
        return filtered
    
    def select_workflow(self, workflow_id: str) -> bool:
        """
        Select a workflow to display.
        
        Args:
            workflow_id: ID of workflow to select
            
        Returns:
            True if selection was successful
        """
        try:
            self.selected_workflow_id = workflow_id
            
            # Get workflow data
            workflow_data = self.state_manager.get_workflow(workflow_id)
            if not workflow_data:
                self.logger.warning(f"Workflow {workflow_id} not found in state")
                return False
            
            # Update task table
            self._update_task_table(workflow_data)
            
            # Update workflow details
            self._update_workflow_details(workflow_data)
            
            # Update progress bar and summary
            self._update_progress_bar(workflow_data)
            self._update_status_summary(workflow_data)
            
            # Update dependency visualization
            self._update_dependency_graph(workflow_data)
            
            return True
        except Exception as e:
            self.logger.error(f"Error selecting workflow {workflow_id}: {str(e)}")
            return False
    
    def _update_task_table(self, workflow_data: Dict[str, Any]) -> None:
        """Update the task table with workflow tasks."""
        # Clear existing rows
        self.task_table.clear()
        
        # Get tasks from workflow data
        wf_info = workflow_data.get('data', {})
        tasks = wf_info.get('tasks', [])
        
        # Apply filters
        filtered_tasks = self._filter_tasks(tasks)
        
        # Use performance optimization for large datasets
        if len(filtered_tasks) > 10:
            # For large datasets, use pagination
            paginated_tasks = self.performance_optimizer.get_paginated_tasks(
                filtered_tasks,
                page=1,
                page_size=100
            )
        else:
            paginated_tasks = filtered_tasks
        
        # Add task rows
        for task in paginated_tasks:
            task_id = task.get('id', 'unknown')
            status = task.get('status', 'unknown')
            cycle = task.get('cycle', 'N/A')
            start_time = task.get('start_time', 'N/A')
            end_time = task.get('end_time', 'N/A')
            
            # Calculate duration if both times are available
            duration = 'N/A'
            if start_time != 'N/A' and end_time != 'N/A':
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration = FormattingUtils.format_duration((end_dt - start_dt).total_seconds())
                except:
                    duration = 'N/A'
            
            # Create status text with color
            status_text = StatusVisualization.format_status_text(status).markup
            
            self.task_table.add_row(
                task_id,
                status_text,
                cycle,
                start_time,
                end_time,
                duration
            )
        
        # Add summary if we're showing a subset
        if len(filtered_tasks) > len(paginated_tasks):
            self.task_table.add_row(
                f"Showing {len(paginated_tasks)} of {len(filtered_tasks)} tasks",
                "...",
                "...",
                "...",
                "...",
                "..."
            )
    def _update_task_table_with_filtered_tasks(self, tasks: List[Dict[str, Any]]) -> None:
        """Update the task table with a pre-filtered list of tasks."""
        # Clear existing rows
        self.task_table.clear()
        
        # Add task rows
        for task in tasks:
            task_id = task.get('id', 'unknown')
            status = task.get('status', 'unknown')
            cycle = task.get('cycle', 'N/A')
            start_time = task.get('start_time', 'N/A')
            end_time = task.get('end_time', 'N/A')
            
            # Calculate duration if both times are available
            duration = 'N/A'
            if start_time != 'N/A' and end_time != 'N/A':
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    duration = FormattingUtils.format_duration((end_dt - start_dt).total_seconds())
                except:
                    duration = 'N/A'
            
            # Create status text with color
            status_text = StatusVisualization.format_status_text(status).markup
            
            self.task_table.add_row(
                task_id,
                status_text,
                cycle,
                start_time,
                end_time,
                duration
            )
        
        # Reset filter state to show all after dependency filtering
        self.filter_state = ""
    
    def _update_workflow_details(self, workflow_data: Dict[str, Any]) -> None:
        """Update the workflow details panel."""
        wf_info = workflow_data.get('data', {})
        
        details_text = f"""
Workflow: {self.selected_workflow_id}
Name: {wf_info.get('name', 'N/A')}
Description: {wf_info.get('description', 'N/A')}
Status: {workflow_data.get('status', 'unknown')}
Last Updated: {workflow_data.get('last_updated', 'N/A')}
Total Tasks: {len(wf_info.get('tasks', []))}
Total Cycles: {len(wf_info.get('cycles', []))}
        """.strip()
        
        self.workflow_details.update(details_text)
    
    def _update_progress_bar(self, workflow_data: Dict[str, Any]) -> None:
        """Update the workflow progress bar."""
        wf_info = workflow_data.get('data', {})
        tasks = wf_info.get('tasks', [])
        
        if not tasks:
            self.progress_bar.progress = 0.0
            return
        
        progress_percent, _ = StatusVisualization.calculate_workflow_progress(tasks)
        self.progress_bar.progress = progress_percent  # Value is 0-100
    
    def _update_status_summary(self, workflow_data: Dict[str, Any]) -> None:
        """Update the status summary panel."""
        wf_info = workflow_data.get('data', {})
        tasks = wf_info.get('tasks', [])
        
        if not tasks:
            self.status_summary.update("No tasks to display")
            return
        
        summary = FormattingUtils.format_task_summary(tasks)
        
        summary_text = f"""
Status Summary:
  Total: {summary['total']}
  Success: {summary['success']}
  Failed: {summary['failed']}
  Running: {summary['running']}
  Queued: {summary['queued']}
  Held: {summary['held']}
  Unknown: {summary['unknown']}
        """.strip()
        
        self.status_summary.update(summary_text)
    
    def _update_dependency_graph(self, workflow_data: Dict[str, Any]) -> None:
        """Update the dependency visualization."""
        wf_info = workflow_data.get('data', {})
        tasks = wf_info.get('tasks', [])
        
        if not tasks:
            self.dependency_graph.update("No dependencies to display")
            return
        
        # Use performance optimization for large workflows
        if len(tasks) > 10:
            # For large workflows, use optimized dependency calculation
            optimized_deps = self.performance_optimizer.calculate_render_optimized_tree(tasks, max_depth=3)
            dep_text = "Large workflow - showing optimized dependency view:\n"
            for group in optimized_deps:
                dep_text += f" {group['name']}: {group['count']} tasks\n"
        else:
            # Use the dependency visualization utility
            dep_text = DependencyVisualization.create_dependency_graph(tasks, max_display=15)
        
        self.dependency_graph.update(dep_text)
    
    def watch_selected_workflow_id(self, old_value: str, new_value: str) -> None:
        """Called when the selected workflow ID changes."""
        if new_value:
            self.select_workflow(new_value)
    
    def refresh_view(self) -> None:
        """
        Refresh the workflow display with current state data.
        """
        try:
            self.update_workflows()
            if self.selected_workflow_id:
                self.select_workflow(self.selected_workflow_id)
        except Exception as e:
            self.logger.error(f"Error refreshing workflow viewer: {str(e)}")
    
    def get_selected_workflow_id(self) -> Optional[str]:
        """
        Get the currently selected workflow ID.
        
        Returns:
            Currently selected workflow ID or None
        """
        return self.selected_workflow_id
    
    def get_workflow_summary(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get a summary of the specified workflow (or selected workflow).
        
        Args:
            workflow_id: ID of workflow to summarize (uses selected if None)
            
        Returns:
            Dictionary with workflow summary
        """
        target_id = workflow_id or self.selected_workflow_id
        if not target_id:
            return {}
        
        workflow_data = self.state_manager.get_workflow(target_id)
        if not workflow_data:
            return {}
        
        wf_info = workflow_data.get('data', {})
        tasks = wf_info.get('tasks', [])
        
        # Count task statuses
        status_counts = {}
        for task in tasks:
            status = task.get('status', 'unknown').lower()
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'id': target_id,
            'name': wf_info.get('name', target_id),
            'description': wf_info.get('description', ''),
            'status': workflow_data.get('status', 'unknown'),
            'total_tasks': len(tasks),
            'task_statuses': status_counts,
            'total_cycles': len(wf_info.get('cycles', [])),
            'total_resources': len(wf_info.get('resources', [])),
            'last_updated': workflow_data.get('last_updated', 'N/A')
        }
    
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection in the workflow tree."""
        if event.node.data:  # If the node has data (workflow ID)
            workflow_id = event.node.data
            self.select_workflow(workflow_id)
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in the task table."""
        try:
            task_id = self.task_table.get_cell_at(Coordinate(event.cursor_row, 0))
            self.selected_task_id = task_id.plain

            # Emit task selected event
            self.post_message(self.TaskSelected(self.selected_task_id))
        except Exception as e:
            self.logger.error(f"Error getting task from row {event.cursor_row}: {e}")
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events for filters."""
        button_id = event.button.id
        if button_id == "filter-all":
            self.filter_state = ""
        elif button_id == "filter-running":
            self.filter_state = "running"
        elif button_id == "filter-failed":
            self.filter_state = "failed"
        elif button_id == "filter-success":
            self.filter_state = "success"
        elif button_id == "filter-dependencies":
            self.filter_state = "dependencies"
        elif button_id == "show-circular":
            self.filter_state = "circular"
        elif button_id == "filter-upstream":
            # This would filter to show upstream dependencies of selected task
            if self.selected_task_id:
                workflow_data = self.state_manager.get_workflow(self.selected_workflow_id)
                if workflow_data:
                    tasks = workflow_data.get('data', {}).get('tasks', [])
                    filtered_tasks = DependencyVisualization.filter_tasks_by_dependency(
                        tasks, self.selected_task_id, 'upstream'
                    )
                    # For now, just update the display with these tasks
                    self._update_task_table_with_filtered_tasks(filtered_tasks)
        elif button_id == "filter-downstream":
            # This would filter to show downstream dependents of selected task
            if self.selected_task_id:
                workflow_data = self.state_manager.get_workflow(self.selected_workflow_id)
                if workflow_data:
                    tasks = workflow_data.get('data', {}).get('tasks', [])
                    filtered_tasks = DependencyVisualization.filter_tasks_by_dependency(
                        tasks, self.selected_task_id, 'downstream'
                    )
                    # For now, just update the display with these tasks
                    self._update_task_table_with_filtered_tasks(filtered_tasks)
    
    def on_key(self, event) -> None:
        """Handle keyboard events for navigation and interaction."""
        # Task table navigation
        if event.key == "up" and self.task_table.has_focus:
            self.task_table.move_cursor(row=-1, animate=True)
        elif event.key == "down" and self.task_table.has_focus:
            self.task_table.move_cursor(row=1, animate=True)
        elif event.key == "enter" and self.task_table.has_focus:
            # Handle enter key on selected task
            cursor_row = self.task_table.cursor_row
            if cursor_row < self.task_table.row_count:
                task_id = self.task_table.get_cell_at(Coordinate(cursor_row, 0)).plain
                self.selected_task_id = task_id
                self.post_message(self.TaskSelected(task_id))
        elif event.key == "f2" and self.task_table.has_focus:
            # Show context menu for task with F2 key
            cursor_row = self.task_table.cursor_row
            if cursor_row < self.task_table.row_count:
                task_id = self.task_table.get_cell_at(Coordinate(cursor_row, 0)).plain
                self.selected_task_id = task_id
                # Get current cursor position for context menu
                cursor_x, cursor_y = self.task_table.size
                self._show_task_context_menu(cursor_x // 2, cursor_y // 2)  # Center of table
        elif event.key == "ctrl+r":
            # Refresh current workflow
            if self.selected_workflow_id:
                self.select_workflow(self.selected_workflow_id)
        elif event.key == "ctrl+f":
            # Focus on search input
            self.search_input.focus()
        elif event.key == "/":
            # Focus on search input with forward slash
            self.search_input.focus()
        elif event.key == "escape":
            # Hide context menu if visible
            if self.context_menu_visible:
                self.context_menu.update("")
                self.context_menu_visible = False
                self.context_menu_visible = False
    
    def on_right_click(self, event) -> None:
        """Handle right-click events to show context menu."""
        # Determine what was right-clicked and show appropriate context menu
        if self.task_table.has_focus and self.selected_task_id:
            self._show_task_context_menu(event.x, event.y)
        elif self.workflow_tree.has_focus and self.selected_workflow_id:
            self._show_workflow_context_menu(event.x, event.y)
    
    def _show_task_context_menu(self, x: int, y: int) -> None:
        """Show context menu for task."""
        menu_content = """
[bold]Task Actions:[/bold]
- [green]View Task Logs[/green] (V)
- [yellow]Retry Task[/yellow] (R)
- [blue]Hold Task[/blue] (H)
- [cyan]Release Task[/cyan] (L)
- [magenta]Task Details[/magenta] (D)
- [red]Kill Task[/red] (K)
        """
        self.context_menu.update(menu_content)
        self.context_menu.styles.offset = (x, y)
        self.context_menu_visible = True
    
    def _show_workflow_context_menu(self, x: int, y: int) -> None:
        """Show context menu for workflow."""
        menu_content = """
[bold]Workflow Actions:[/bold]
- [green]Refresh Workflow[/green] (Ctrl+R)
- [blue]View Workflow Logs[/blue] (V)
- [yellow]Export Workflow Data[/yellow] (E)
- [magenta]Workflow Details[/magenta] (D)
- [cyan]Show Dependencies[/cyan] (G)
- [red]Cancel Workflow[/red] (C)
        """
        self.context_menu.update(menu_content)
        self.context_menu.styles.offset = (x, y)
        self.context_menu_visible = True
    
    class WorkflowSelected(Message):
        """Message sent when a workflow is selected."""
        
        def __init__(self, workflow_id: str) -> None:
            super().__init__()
            self.workflow_id = workflow_id
    
    class TaskSelected(Message):
        """Message sent when a task is selected."""
        
        def __init__(self, task_id: str) -> None:
            super().__init__()
            self.task_id = task_id
    
    class WorkflowUpdated(Message):
        """Message sent when workflow data is updated."""
        
        def __init__(self, workflow_id: str) -> None:
            super().__init__()
            self.workflow_id = workflow_id
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle changes to the search input."""
        if event.input.id == "search-input":
            self.search_term = event.value
            # Update the display to reflect the new search term
            if self.selected_workflow_id:
                workflow_data = self.state_manager.get_workflow(self.selected_workflow_id)
                if workflow_data:
                    self._update_task_table(workflow_data)