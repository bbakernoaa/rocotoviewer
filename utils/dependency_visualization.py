"""
Dependency visualization utilities for RocotoViewer.

This module provides utilities for visualizing task dependencies
in workflows with various visualization formats.
"""

from typing import Dict, Any, List, Tuple, Optional
from collections import defaultdict, deque
import logging

from rich.text import Text
from rich.tree import Tree as RichTree
from rich.panel import Panel
from rich.columns import Columns


class DependencyVisualization:
    """
    Utility class for dependency visualization in RocotoViewer.
    """
    
    logger = logging.getLogger(__name__)
    
    @classmethod
    def create_dependency_graph(cls, tasks: List[Dict[str, Any]], max_display: int = 20) -> str:
        """
        Create a text-based dependency graph for tasks.
        
        Args:
            tasks: List of task dictionaries
            max_display: Maximum number of tasks to display in the graph
            
        Returns:
            String representation of dependency graph
        """
        if not tasks:
            return "No dependencies to display"
        
        # Build dependency relationships
        dependencies = defaultdict(list)  # task_id -> [dependent_task_ids]
        dependents = defaultdict(list)   # task_id -> [dependency_task_ids]
        
        for task in tasks:
            task_id = task.get('id', 'unknown')
            task_deps = task.get('dependencies', [])
            
            for dep in task_deps:
                target = dep.get('target', dep.get('condition', ''))
                if target and target != task_id: # Avoid self-dependencies
                    dependencies[target].append(task_id)
                    dependents[task_id].append(target)
        
        if not dependencies and not dependents:
            return "No dependencies found"
        
        # Create dependency visualization
        graph_lines = ["Dependency Graph:", "================="]
        
        # Show tasks with their dependencies
        displayed_count = 0
        for task in tasks[:max_display]:
            task_id = task.get('id', 'unknown')
            deps = dependents.get(task_id, [])
            dependents_list = dependencies.get(task_id, [])
            
            if deps or dependents_list:
                graph_lines.append(f"  {task_id}")
                if deps:
                    graph_lines.append(f"    depends on: {', '.join(deps[:5])}")  # Limit to 5 deps
                    if len(deps) > 5:
                        graph_lines.append(f"    ... and {len(deps) - 5} more")
                if dependents_list:
                    graph_lines.append(f"    required by: {', '.join(dependents_list[:5])}")  # Limit to 5 dependents
                    if len(dependents_list) > 5:
                        graph_lines.append(f"    ... and {len(dependents_list) - 5} more")
                
                displayed_count += 1
                if displayed_count >= max_display:
                    if len(tasks) > max_display:
                        graph_lines.append(f"\n ... and {len(tasks) - max_display} more tasks")
                    break
        
        return "\n".join(graph_lines)
    
    @classmethod
    def create_dependency_tree(cls, tasks: List[Dict[str, Any]], max_depth: int = 3) -> str:
        """
        Create a hierarchical dependency tree.
        
        Args:
            tasks: List of task dictionaries
            max_depth: Maximum depth to display in the tree
            
        Returns:
            String representation of dependency tree
        """
        if not tasks:
            return "No dependencies to display"
        
        # Build dependency graph
        dependency_graph = defaultdict(list)
        all_task_ids = {task.get('id') for task in tasks if task.get('id')}
        
        for task in tasks:
            task_id = task.get('id', 'unknown')
            task_deps = task.get('dependencies', [])
            
            for dep in task_deps:
                target = dep.get('target', dep.get('condition', ''))
                if target in all_task_ids and target != task_id:
                    dependency_graph[target].append(task_id)
        
        if not dependency_graph:
            return "No dependencies found"
        
        # Find root tasks (tasks with no dependencies on other tasks in the list)
        all_dependents = set()
        for deps in dependency_graph.values():
            all_dependents.update(deps)
        
        root_tasks = [task.get('id') for task in tasks 
                     if task.get('id') and task.get('id') not in all_dependents]
        
        if not root_tasks:
            return "Circular dependencies detected - no root tasks found"
        
        # Build tree representation
        tree_lines = ["Dependency Tree:", "================"]
        
        def _build_tree_recursive(task_id: str, depth: int = 0, visited: set = None) -> List[str]:
            if visited is None:
                visited = set()
            
            if depth >= max_depth or task_id in visited:
                return []
            
            visited.add(task_id)
            lines = ["  " * depth + f"├─ {task_id}"]
            
            children = dependency_graph.get(task_id, [])
            for child in children[:10]:  # Limit to 10 children per level
                lines.extend(_build_tree_recursive(child, depth + 1, visited.copy()))
            
            if len(children) > 10:
                lines.append("  " * (depth + 1) + f"└─ ... and {len(children) - 10} more")
            
            return lines
        
        for root_task in root_tasks[:5]:  # Limit to 5 root tasks
            tree_lines.extend(_build_tree_recursive(root_task))
        
        if len(root_tasks) > 5:
            tree_lines.append(f"... and {len(root_tasks) - 5} more root tasks")
        
        return "\n".join(tree_lines)
    
    @classmethod
    def find_circular_dependencies(cls, tasks: List[Dict[str, Any]]) -> List[List[str]]:
        """
        Find circular dependencies in the task list.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            List of circular dependency cycles
        """
        if not tasks:
            return []
        
        # Build dependency graph
        graph = defaultdict(list)
        all_task_ids = {task.get('id') for task in tasks if task.get('id')}
        
        for task in tasks:
            task_id = task.get('id', 'unknown')
            task_deps = task.get('dependencies', [])
            
            for dep in task_deps:
                target = dep.get('target', dep.get('condition', ''))
                if target in all_task_ids and target != task_id:
                    graph[task_id].append(target)
        
        # Find cycles using DFS
        visited = set()
        rec_stack = []
        cycles = []
        
        def dfs(node: str, path: List[str]):
            if node in rec_stack:
                cycle_start_idx = path.index(node)
                cycle = path[cycle_start_idx:] + [node]
                if cycle not in cycles:
                    cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.append(node)
            path.append(node)
            
            for neighbor in graph[node]:
                dfs(neighbor, path.copy())
            
            rec_stack.pop()
            path.pop()
        
        for task in tasks:
            task_id = task.get('id')
            if task_id and task_id not in visited:
                dfs(task_id, [])
        
        return cycles
    
    @classmethod
    def get_dependency_statistics(cls, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about dependencies in the task list.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            Dictionary with dependency statistics
        """
        if not tasks:
            return {
                'total_tasks': 0,
                'total_dependencies': 0,
                'tasks_with_dependencies': 0,
                'tasks_with_dependents': 0,
                'orphan_tasks': 0,
                'max_dependency_depth': 0
            }
        
        # Build dependency relationships
        dependencies = defaultdict(list)  # task_id -> [dependent_task_ids]
        dependents = defaultdict(list)   # task_id -> [dependency_task_ids]
        
        all_task_ids = {task.get('id') for task in tasks if task.get('id')}
        
        for task in tasks:
            task_id = task.get('id', 'unknown')
            task_deps = task.get('dependencies', [])
            
            for dep in task_deps:
                target = dep.get('target', dep.get('condition', ''))
                if target in all_task_ids and target != task_id:
                    dependencies[target].append(task_id)
                    dependents[task_id].append(target)
        
        # Calculate statistics
        tasks_with_deps = sum(1 for deps in dependents.values() if deps)
        tasks_with_dependents = sum(1 for deps in dependencies.values() if deps)
        
        # Find orphan tasks (tasks with no dependencies and no dependents)
        orphan_tasks = 0
        for task in tasks:
            task_id = task.get('id')
            if task_id:
                has_deps = task_id in dependents and len(dependents[task_id]) > 0
                has_dependents = task_id in dependencies and len(dependencies[task_id]) > 0
                if not has_deps and not has_dependents:
                    orphan_tasks += 1
        
        # Calculate max dependency depth using BFS
        max_depth = 0
        if dependencies:
            # Find root tasks (tasks with no dependencies)
            all_dependents = set()
            for deps in dependencies.values():
                all_dependents.update(deps)
            
            root_tasks = [task.get('id') for task in tasks 
                         if task.get('id') and task.get('id') not in all_dependents]
            
            for root in root_tasks:
                depth = cls._calculate_depth(root, dependencies)
                max_depth = max(max_depth, depth)
        
        return {
            'total_tasks': len(tasks),
            'total_dependencies': sum(len(deps) for deps in dependents.values()),
            'tasks_with_dependencies': tasks_with_deps,
            'tasks_with_dependents': tasks_with_dependents,
            'orphan_tasks': orphan_tasks,
            'max_dependency_depth': max_depth
        }
    
    @classmethod
    def _calculate_depth(cls, start_task: str, dependency_graph: Dict[str, List[str]]) -> int:
        """
        Calculate the maximum depth from a starting task using BFS.
        
        Args:
            start_task: Starting task ID
            dependency_graph: Dependency graph (task_id -> [dependent_task_ids])
            
        Returns:
            Maximum depth from the starting task
        """
        if start_task not in dependency_graph:
            return 0
        
        queue = deque([(start_task, 0)])
        visited = {start_task}
        max_depth = 0
        
        while queue:
            current_task, depth = queue.popleft()
            max_depth = max(max_depth, depth)
            
            for dependent in dependency_graph.get(current_task, []):
                if dependent not in visited:
                    visited.add(dependent)
                    queue.append((dependent, depth + 1))
        
        return max_depth + 1 # Add 1 to count the starting task
    
    @classmethod
    def filter_tasks_by_dependency(cls, tasks: List[Dict[str, Any]], 
                                   task_id: str, 
                                   direction: str = 'both') -> List[Dict[str, Any]]:
        """
        Filter tasks based on their dependency relationship with a specific task.
        
        Args:
            tasks: List of task dictionaries
            task_id: Task ID to filter by
            direction: 'upstream', 'downstream', or 'both'
            
        Returns:
            List of tasks that have dependency relationship with the specified task
        """
        if not tasks:
            return []
        
        # Build dependency relationships
        dependencies = defaultdict(list)  # task_id -> [dependent_task_ids]
        dependents = defaultdict(list)   # task_id -> [dependency_task_ids]
        
        all_task_ids = {task.get('id') for task in tasks if task.get('id')}
        
        for task in tasks:
            task_id_temp = task.get('id', 'unknown')
            task_deps = task.get('dependencies', [])
            
            for dep in task_deps:
                target = dep.get('target', dep.get('condition', ''))
                if target in all_task_ids and target != task_id_temp:
                    dependencies[target].append(task_id_temp)
                    dependents[task_id_temp].append(target)
        
        # Find related tasks based on direction
        related_tasks = set()
        
        if direction in ['upstream', 'both']:
            # Find all upstream dependencies (tasks this task depends on)
            queue = deque(dependents.get(task_id, []))
            visited = set()
            
            while queue:
                current = queue.popleft()
                if current not in visited:
                    visited.add(current)
                    related_tasks.add(current)
                    # Add the dependencies of this task
                    queue.extend(dependents.get(current, []))
        
        if direction in ['downstream', 'both']:
            # Find all downstream dependents (tasks that depend on this task)
            queue = deque(dependencies.get(task_id, []))
            visited = set()
            
            while queue:
                current = queue.popleft()
                if current not in visited:
                    visited.add(current)
                    related_tasks.add(current)
                    # Add the dependents of this task
                    queue.extend(dependencies.get(current, []))
        
        # Include the original task if it exists
        if task_id in all_task_ids:
            related_tasks.add(task_id)
        
        # Return tasks that are in the related set
        return [task for task in tasks if task.get('id') in related_tasks]


# Create a singleton instance for convenience
dependency_visualization = DependencyVisualization()