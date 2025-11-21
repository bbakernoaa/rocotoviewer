"""
State management module for RocotoViewer.

This module manages the application state, including workflow data,
UI state, and user preferences with enhanced support for workflow visualization.
"""

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import logging
from collections import defaultdict


class StateManager:
    """
    Enhanced state manager for application state including workflow data, UI state, and user preferences.
    """
    
    def __init__(self, config):
        """
        Initialize the state manager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Application state
        self._state_lock = threading.RLock()
        self._state = {
            'workflows': {},
            'ui': {
                'current_view': 'main',
                'selected_workflow': None,
                'selected_task': None,
                'theme': getattr(config.display, 'theme', 'default'),
                'refresh_interval': getattr(config.display, 'refresh_interval', 1),
                'workflow_filters': {
                    'status': None,
                    'search': '',
                    'show_dependencies': True,
                    'show_progress': True
                }
            },
            'user_preferences': {},
            'session_data': {
                'start_time': datetime.now(),
                'active_tasks': [],
                'recent_files': [],
                'workflow_stats': {
                    'total_workflows': 0,
                    'total_tasks': 0,
                    'status_counts': defaultdict(int)
                }
            },
            'visualization': {
                'dependency_layout': 'hierarchical',  # 'hierarchical', 'circular', 'grid'
                'color_scheme': 'default',
                'node_size': 'medium',
                'show_labels': True,
                'animation_enabled': True
            }
        }
        
        # Event callbacks
        self._change_callbacks: List[Callable] = []
        
        # Workflow state change callbacks
        self._workflow_callbacks: List[Callable] = []
        
        # Load saved state if available
        self.load_state()
    
    def register_change_callback(self, callback: Callable):
        """
        Register a callback to be called when state changes.
        
        Args:
            callback: Function to call when state changes
        """
        with self._state_lock:
            self._change_callbacks.append(callback)
    
    def register_workflow_callback(self, callback: Callable):
        """
        Register a callback to be called when workflow state changes.
        
        Args:
            callback: Function to call when workflow state changes
        """
        with self._state_lock:
            self._workflow_callbacks.append(callback)
    
    def _notify_change(self, key: str, value: Any):
        """
        Notify registered callbacks of a state change.
        
        Args:
            key: Key that changed
            value: New value
        """
        for callback in self._change_callbacks:
            try:
                callback(key, value)
            except Exception as e:
                self.logger.error(f"Error in state change callback: {str(e)}")
    
    def _notify_workflow_change(self, workflow_id: str, workflow_data: Dict[str, Any], change_type: str):
        """
        Notify registered workflow callbacks of a workflow state change.
        
        Args:
            workflow_id: ID of the workflow that changed
            workflow_data: New workflow data
            change_type: Type of change ('added', 'updated', 'removed')
        """
        for callback in self._workflow_callbacks:
            try:
                callback(workflow_id, workflow_data, change_type)
            except Exception as e:
                self.logger.error(f"Error in workflow change callback: {str(e)}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the state.
        
        Args:
            key: Key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            Value from state or default
        """
        with self._state_lock:
            keys = key.split('.')
            current = self._state
            
            for k in keys:
                if isinstance(current, dict) and k in current:
                    current = current[k]
                else:
                    return default
            
            return current
    
    def set(self, key: str, value: Any):
        """
        Set a value in the state.
        
        Args:
            key: Key to set
            value: Value to set
        """
        with self._state_lock:
            keys = key.split('.')
            current = self._state
            
            # Navigate to the parent of the target key
            for k in keys[:-1]:
                if k not in current or not isinstance(current[k], dict):
                    current[k] = {}
                current = current[k]
            
            # Set the final key
            final_key = keys[-1]
            old_value = current.get(final_key)
            current[final_key] = value
            
            # Notify of change
            self._notify_change(key, value)
            
            # Log significant changes
            if key.startswith('workflows.'):
                self.logger.info(f"Workflow state updated: {key}")
            elif key.startswith('ui.'):
                self.logger.debug(f"UI state updated: {key}")
    
    def update_workflow(self, workflow_id: str, workflow_data: Dict[str, Any]):
        """
        Update workflow data in the state with enhanced tracking.
        
        Args:
            workflow_id: Unique identifier for the workflow
            workflow_data: Workflow data to store
        """
        # Calculate workflow statistics
        stats = self._calculate_workflow_stats(workflow_data)
        
        key = f'workflows.{workflow_id}'
        workflow_entry = {
            'data': workflow_data,
            'last_updated': datetime.now().isoformat(),
            'status': workflow_data.get('status', 'unknown'),
            'stats': stats,
            'visualization': {
                'position': workflow_data.get('visualization', {}).get('position', {'x': 0, 'y': 0}),
                'expanded': workflow_data.get('visualization', {}).get('expanded', True),
                'highlighted': workflow_data.get('visualization', {}).get('highlighted', False)
            }
        }
        
        self.set(key, workflow_entry)
        
        # Update session workflow statistics
        self._update_session_stats(workflow_id, workflow_entry)
        
        # Notify workflow change
        self._notify_workflow_change(workflow_id, workflow_entry, 'updated')
    
    def _calculate_workflow_stats(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate statistics for a workflow.
        
        Args:
            workflow_data: Workflow data to analyze
            
        Returns:
            Dictionary with workflow statistics
        """
        tasks = workflow_data.get('tasks', [])
        stats = {
            'total_tasks': len(tasks),
            'status_counts': defaultdict(int),
            'completion_percentage': 0,
            'active_tasks': 0,
            'failed_tasks': 0,
            'successful_tasks': 0,
            'running_tasks': 0
        }
        
        # Count task statuses
        for task in tasks:
            status = task.get('status', 'unknown').lower()
            stats['status_counts'][status] += 1
            
            if status in ['success', 'succeeded', 'completed']:
                stats['successful_tasks'] += 1
            elif status in ['failed', 'error']:
                stats['failed_tasks'] += 1
            elif status in ['running', 'active', 'r']:
                stats['running_tasks'] += 1
            elif status in ['queued', 'pending', 'q']:
                stats['active_tasks'] += 1
        
        # Calculate completion percentage
        if stats['total_tasks'] > 0:
            stats['completion_percentage'] = (stats['successful_tasks'] / stats['total_tasks']) * 10
        
        return stats
    
    def _update_session_stats(self, workflow_id: str, workflow_entry: Dict[str, Any]):
        """
        Update session-level statistics based on workflow changes.
        
        Args:
            workflow_id: ID of the workflow
            workflow_entry: Workflow entry with data and stats
        """
        with self._state_lock:
            # Update total workflow count
            self._state['session_data']['workflow_stats']['total_workflows'] = len(self._state['workflows'])
            
            # Update total task count
            total_tasks = sum(wf.get('stats', {}).get('total_tasks', 0) for wf in self._state['workflows'].values())
            self._state['session_data']['workflow_stats']['total_tasks'] = total_tasks
            
            # Reset status counts
            self._state['session_data']['workflow_stats']['status_counts'] = defaultdict(int)
            
            # Recalculate all status counts
            for wf_id, wf_data in self._state['workflows'].items():
                stats = wf_data.get('stats', {})
                for status, count in stats.get('status_counts', {}).items():
                    self._state['session_data']['workflow_stats']['status_counts'][status] += count
    
    def remove_workflow(self, workflow_id: str):
        """
        Remove workflow data from the state.
        
        Args:
            workflow_id: Unique identifier for the workflow to remove
        """
        with self._state_lock:
            if 'workflows' in self._state:
                removed_data = self._state['workflows'].pop(workflow_id, None)
                if removed_data is not None:
                    self._notify_change(f'workflows.{workflow_id}', None)
                    self._notify_workflow_change(workflow_id, removed_data, 'removed')
                    
                    # Update session stats
                    self._update_session_stats(workflow_id, removed_data)
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get workflow data from the state.
        
        Args:
            workflow_id: Unique identifier for the workflow
            
        Returns:
            Workflow data or None if not found
        """
        workflow_data = self.get(f'workflows.{workflow_id}')
        if workflow_data is None:
            return None
        return workflow_data
    
    def get_all_workflows(self) -> Dict[str, Any]:
        """
        Get all workflow data from the state.
        
        Returns:
            Dictionary of all workflow data
        """
        return self.get('workflows', {})
    
    def get_filtered_workflows(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get workflows filtered by specified criteria.
        
        Args:
            filters: Dictionary with filter criteria
            
        Returns:
            Dictionary of filtered workflow data
        """
        all_workflows = self.get_all_workflows()
        
        if not filters:
            filters = self.get('ui.workflow_filters', {})
        
        filtered_workflows = {}
        
        for workflow_id, workflow_data in all_workflows.items():
            include = True
            
            # Apply status filter
            if filters.get('status') and workflow_data and workflow_data.get('status') != filters['status']:
                include = False
            
            # Apply search filter
            if filters.get('search') and workflow_data:
                search_term = filters['search'].lower()
                workflow_name = workflow_data.get('data', {}).get('name', '').lower()
                if search_term not in workflow_name:
                    include = False
            
            if include:
                filtered_workflows[workflow_id] = workflow_data
        
        return filtered_workflows
    
    def add_recent_file(self, file_path: str):
        """
        Add a file to the recent files list.
        
        Args:
            file_path: Path to add to recent files
        """
        recent_files = self.get('session_data.recent_files', [])
        if file_path in recent_files:
            recent_files.remove(file_path)
        recent_files.insert(0, file_path)
        
        # Keep only the 10 most recent files
        recent_files = recent_files[:10]
        self.set('session_data.recent_files', recent_files)
    
    def update_from_file_change(self, event_type: str, file_path: str):
        """
        Update state based on a file system change event.
        
        Args:
            event_type: Type of file system event (created, modified, deleted, etc.)
            file_path: Path to the file that changed
        """
        self.logger.debug(f"Processing file change: {event_type} {file_path}")
        
        # Add to recent files
        self.add_recent_file(file_path)
        
        # In a real implementation, this would trigger workflow re-parsing
        # and state updates based on the changed file
        if event_type in ['modified', 'created']:
            # Mark workflows as needing refresh
            pass
    
    def save_state(self, state_file: Optional[Path] = None):
        """
        Save the current state to a file.
        
        Args:
            state_file: Path to save state (defaults to configured path)
        """
        save_path = state_file or Path.home() / '.rocotoviewer' / 'state.json'
        
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create a copy of the state without sensitive data
            state_copy = self._get_safe_state_copy()
            
            with open(save_path, 'w') as f:
                json.dump(state_copy, f, indent=2, default=str)
            
            self.logger.info(f"State saved to {save_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving state: {str(e)}")
    
    def load_state(self, state_file: Optional[Path] = None):
        """
        Load state from a file.
        
        Args:
            state_file: Path to load state from (defaults to configured path)
        """
        load_path = state_file or Path.home() / '.rocotoviewer' / 'state.json'
        
        if not load_path.exists():
            self.logger.debug(f"State file does not exist: {load_path}")
            return
        
        try:
            with open(load_path, 'r') as f:
                saved_state = json.load(f)
            
            # Merge saved state with current state
            self._merge_state(saved_state)
            self.logger.info(f"State loaded from {load_path}")
            
        except Exception as e:
            self.logger.error(f"Error loading state: {str(e)}")
    
    def _get_safe_state_copy(self) -> Dict[str, Any]:
        """
        Get a copy of the state with sensitive data removed.
        
        Returns:
            Safe copy of the state
        """
        # Create a deep copy of the state
        import copy
        state_copy = copy.deepcopy(self._state)
        
        # Remove any sensitive data (in this example, we don't have any)
        # In a real implementation, you might remove API keys, passwords, etc.
        
        return state_copy
    
    def _merge_state(self, saved_state: Dict[str, Any]):
        """
        Merge saved state with current state.
        
        Args:
            saved_state: State to merge
        """
        # This is a simple implementation - in a real app you might want
        # more sophisticated merging logic
        with self._state_lock:
            self._state.update(saved_state)
    
    def reset(self):
        """Reset the state to default values."""
        with self._state_lock:
            self._state = {
                'workflows': {},
                'ui': {
                    'current_view': 'main',
                    'selected_workflow': None,
                    'selected_task': None,
                    'theme': self.config.display.theme,
                    'refresh_interval': self.config.display.refresh_interval,
                    'workflow_filters': {
                        'status': None,
                        'search': '',
                        'show_dependencies': True,
                        'show_progress': True
                    }
                },
                'user_preferences': {},
                'session_data': {
                    'start_time': datetime.now(),
                    'active_tasks': [],
                    'recent_files': [],
                    'workflow_stats': {
                        'total_workflows': 0,
                        'total_tasks': 0,
                        'status_counts': defaultdict(int)
                    }
                },
                'visualization': {
                    'dependency_layout': 'hierarchical',
                    'color_scheme': 'default',
                    'node_size': 'medium',
                    'show_labels': True,
                    'animation_enabled': True
                }
            }
            
            # Notify of reset
            self._notify_change('state_reset', True)
    
    def get_ui_state(self) -> Dict[str, Any]:
        """
        Get UI-specific state.
        
        Returns:
            UI state dictionary
        """
        return self.get('ui', {})
    
    def set_ui_state(self, ui_state: Dict[str, Any]):
        """
        Set UI-specific state.
        
        Args:
            ui_state: UI state dictionary to set
        """
        for key, value in ui_state.items():
            self.set(f'ui.{key}', value)
    
    def get_workflow_stats(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get statistics for a specific workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Statistics dictionary or None if workflow not found
        """
        workflow_data = self.get_workflow(workflow_id)
        if workflow_data:
            return workflow_data.get('stats', {})
        return None
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Get session-level statistics.
        
        Returns:
            Session statistics dictionary
        """
        return self.get('session_data.workflow_stats', {})
    
    def get_visualization_settings(self) -> Dict[str, Any]:
        """
        Get visualization settings.
        
        Returns:
            Visualization settings dictionary
        """
        return self.get('visualization', {})
    
    def set_visualization_settings(self, settings: Dict[str, Any]):
        """
        Set visualization settings.
        
        Args:
            settings: Visualization settings to update
        """
        for key, value in settings.items():
            self.set(f'visualization.{key}', value)
    
    def get_workflow_dependencies(self, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Get dependencies for a specific workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            List of dependency dictionaries
        """
        workflow_data = self.get_workflow(workflow_id)
        if not workflow_data:
            return []
        
        tasks = workflow_data.get('data', {}).get('tasks', [])
        dependencies = []
        
        for task in tasks:
            task_deps = task.get('dependencies', [])
            for dep in task_deps:
                dependencies.append({
                    'source_task': task.get('id'),
                    'target_task': dep.get('target', dep.get('condition', 'unknown')),
                    'dependency_type': dep.get('type', 'unknown'),
                    'attributes': dep.get('attributes', {})
                })
        
        return dependencies
    
    def get_workflow_tasks_by_status(self, workflow_id: str, status: str) -> List[Dict[str, Any]]:
        """
        Get tasks for a workflow filtered by status.
        
        Args:
            workflow_id: ID of the workflow
            status: Status to filter by
            
        Returns:
            List of tasks with the specified status
        """
        workflow_data = self.get_workflow(workflow_id)
        if not workflow_data:
            return []
        
        tasks = workflow_data.get('data', {}).get('tasks', [])
        return [task for task in tasks if task.get('status', '').lower() == status.lower()]
    
    def add_log_entry(self, workflow_id: str, log_entry: Dict[str, Any]):
        """
        Add a log entry to the workflow's log history.
        
        Args:
            workflow_id: ID of the workflow
            log_entry: Log entry to add
        """
        # Initialize log entries if they don't exist
        log_key = f'workflows.{workflow_id}.log_entries'
        current_logs = self.get(log_key, [])
        
        # Add the new log entry
        current_logs.append({
            **log_entry,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only the most recent 1000 log entries
        current_logs = current_logs[-1000:]
        
        self.set(log_key, current_logs)
        
        # Update workflow status based on log entry
        if 'level' in log_entry:
            status = self._determine_status_from_log(log_entry['level'])
            if status:
                self.set(f'workflows.{workflow_id}.data.status', status)
    
    def _determine_status_from_log(self, log_level: str) -> Optional[str]:
        """
        Determine workflow status from log level.
        
        Args:
            log_level: Log level (ERROR, WARNING, INFO, DEBUG)
            
        Returns:
            Status string or None if status shouldn't change
        """
        level = log_level.upper()
        if level in ['ERROR', 'FATAL', 'CRITICAL']:
            return 'FAILED'
        elif level in ['WARNING']:
            return 'WARNING'
        return None