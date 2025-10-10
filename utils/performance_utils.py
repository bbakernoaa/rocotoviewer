"""
Performance utilities for RocotoViewer.

This module provides utilities for optimizing performance when handling large workflows
with thousands of tasks, including efficient data structures, caching, and rendering optimizations.
"""

from typing import List, Dict, Any, Callable, Optional, Generator
import time
import functools
from collections import OrderedDict
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class LRUCache:
    """
    A simple LRU (Least Recently Used) cache implementation for caching expensive operations.
    """
    
    def __init__(self, max_size: int = 128):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        with self.lock:
            if key in self.cache:
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                return self.cache[key]
            return None
    
    def put(self, key: str, value: Any):
        """Put a value in the cache."""
        with self.lock:
            if key in self.cache:
                # Update existing key
                self.cache.move_to_end(key)
            elif len(self.cache) >= self.max_size:
                # Remove least recently used item
                self.cache.popitem(last=False)
            
            self.cache[key] = value
    
    def clear(self):
        """Clear the cache."""
        with self.lock:
            self.cache.clear()


def performance_cache(max_size: int = 128):
    """
    Decorator to cache expensive function calls.
    
    Args:
        max_size: Maximum size of the cache
    """
    def decorator(func: Callable) -> Callable:
        cache = LRUCache(max_size)
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from arguments
            key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            
            # Check if result is in cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Call the function and cache the result
            result = func(*args, **kwargs)
            cache.put(key, result)
            return result
        
        return wrapper
    return decorator


class PerformanceOptimizer:
    """
    Utility class for performance optimizations in RocotoViewer.
    """
    
    def __init__(self):
        self.cache = LRUCache(max_size=256)
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    @performance_cache(max_size=128)
    def calculate_workflow_statistics(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate workflow statistics with caching.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            Dictionary with workflow statistics
        """
        stats = {
            'total_tasks': len(tasks),
            'status_counts': {},
            'completion_percentage': 0,
            'active_tasks': 0,
            'failed_tasks': 0,
            'successful_tasks': 0,
            'running_tasks': 0,
            'max_depth': 0
        }
        
        # Count task statuses
        for task in tasks:
            status = task.get('status', 'unknown').lower()
            stats['status_counts'][status] = stats['status_counts'].get(status, 0) + 1
            
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
    
    def batch_process_tasks(self, tasks: List[Dict[str, Any]], 
                           processor: Callable[[Dict[str, Any]], Any], 
                           batch_size: int = 100) -> List[Any]:
        """
        Process tasks in batches for better performance.
        
        Args:
            tasks: List of task dictionaries
            processor: Function to process each task
            batch_size: Size of each batch
            
        Returns:
            List of processed results
        """
        results = []
        
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = [processor(task) for task in batch]
            results.extend(batch_results)
        
        return results
    
    def filter_tasks_efficiently(self, tasks: List[Dict[str, Any]], 
                                filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Efficiently filter tasks based on multiple criteria.
        
        Args:
            tasks: List of task dictionaries
            filters: Dictionary with filter criteria
            
        Returns:
            List of filtered task dictionaries
        """
        if not filters:
            return tasks
        
        # Use a single pass with multiple conditions
        filtered_tasks = []
        
        for task in tasks:
            include = True
            
            # Apply status filter
            if 'status' in filters and filters['status']:
                if task.get('status', '').lower() != filters['status'].lower():
                    include = False
            
            # Apply search filter
            if include and 'search' in filters and filters['search']:
                search_term = filters['search'].lower()
                task_text = f"{task.get('id', '')} {task.get('status', '')} {task.get('cycle', '')}".lower()
                if search_term not in task_text:
                    include = False
            
            # Apply cycle filter
            if include and 'cycle' in filters and filters['cycle']:
                if filters['cycle'].lower() not in task.get('cycle', '').lower():
                    include = False
            
            if include:
                filtered_tasks.append(task)
        
        return filtered_tasks
    
    def get_paginated_tasks(self, tasks: List[Dict[str, Any]], 
                           page: int = 1, page_size: int = 50) -> List[Dict[str, Any]]:
        """
        Get a paginated subset of tasks for efficient rendering.
        
        Args:
            tasks: List of task dictionaries
            page: Page number (1-indexed)
            page_size: Number of tasks per page
            
        Returns:
            List of paginated task dictionaries
        """
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        return tasks[start_idx:end_idx]
    
    def get_flattened_task_dependencies(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Get a flattened representation of task dependencies for efficient lookup.
        
        Args:
            tasks: List of task dictionaries
            
        Returns:
            Dictionary mapping task IDs to lists of dependent task IDs
        """
        deps = {}
        
        for task in tasks:
            task_id = task.get('id')
            if task_id:
                # Add this task as a dependency for any tasks that depend on it
                for dep in task.get('dependencies', []):
                    target = dep.get('target')
                    if target:
                        if target not in deps:
                            deps[target] = []
                        if task_id not in deps[target]:
                            deps[target].append(task_id)
        
        return deps
    
    def calculate_render_optimized_tree(self, tasks: List[Dict[str, Any]], 
                                      max_depth: int = 5) -> List[Dict[str, Any]]:
        """
        Calculate a render-optimized tree structure for large workflows.
        
        Args:
            tasks: List of task dictionaries
            max_depth: Maximum depth to render
            
        Returns:
            List of optimized tree nodes
        """
        # Group tasks by their status for optimized rendering
        status_groups = {}
        for task in tasks:
            status = task.get('status', 'unknown')
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(task)
        
        # Create optimized structure with limited depth
        optimized = []
        for status, task_list in status_groups.items():
            optimized.append({
                'type': 'group',
                'name': f'{status.upper()} Tasks',
                'count': len(task_list),
                'children': task_list[:max_depth * 10] if len(task_list) > max_depth * 10 else task_list
            })
        
        return optimized
    
    def get_render_bounding_box(self, tasks: List[Dict[str, Any]], 
                               x_range: tuple = (0, 800), 
                               y_range: tuple = (0, 600)) -> Dict[str, Any]:
        """
        Calculate optimal positioning for rendering large numbers of tasks.
        
        Args:
            tasks: List of task dictionaries
            x_range: X coordinate range
            y_range: Y coordinate range
            
        Returns:
            Dictionary with positioning information
        """
        total_tasks = len(tasks)
        if total_tasks == 0:
            return {'positions': {}, 'grid_size': (0, 0)}
        
        # Calculate grid dimensions based on number of tasks
        cols = max(1, int((x_range[1] - x_range[0]) / 100))  # 100px per task width
        rows = max(1, (total_tasks + cols - 1) // cols)  # Ceiling division
        
        positions = {}
        for i, task in enumerate(tasks):
            task_id = task.get('id', f'task_{i}')
            row = i // cols
            col = i % cols
            
            x = x_range[0] + col * 10
            y = y_range[0] + row * 80
            
            positions[task_id] = {'x': x, 'y': y}
        
        return {
            'positions': positions,
            'grid_size': (cols, rows),
            'total_width': cols * 100,
            'total_height': rows * 80
        }


# Create a singleton instance for convenience
performance_optimizer = PerformanceOptimizer()