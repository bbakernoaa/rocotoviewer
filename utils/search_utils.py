"""
Search utilities for RocotoViewer.

This module provides advanced search capabilities for workflows, tasks, and other entities.
"""

from typing import List, Dict, Any, Callable, Optional
import re
from datetime import datetime


class SearchUtils:
    """
    Utility class for search operations in RocotoViewer.
    """
    
    @staticmethod
    def search_workflows(workflows: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Search through workflows based on a query string.
        
        Args:
            workflows: List of workflow dictionaries
            query: Search query string
            
        Returns:
            List of matching workflow dictionaries
        """
        if not query:
            return workflows
        
        query_lower = query.lower()
        results = []
        
        for workflow in workflows:
            # Search in workflow name, id, description, status
            fields_to_search = [
                workflow.get('name', ''),
                workflow.get('id', ''),
                workflow.get('description', ''),
                workflow.get('status', '')
            ]
            
            # Convert all fields to string and check if query is in any
            combined = ' '.join(str(field) for field in fields_to_search).lower()
            if query_lower in combined:
                results.append(workflow)
        
        return results
    
    @staticmethod
    def search_tasks(tasks: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        Search through tasks based on a query string.
        
        Args:
            tasks: List of task dictionaries
            query: Search query string
            
        Returns:
            List of matching task dictionaries
        """
        if not query:
            return tasks
        
        query_lower = query.lower()
        results = []
        
        for task in tasks:
            # Search in task id, status, cycle, command, dependencies
            fields_to_search = [
                task.get('id', ''),
                task.get('status', ''),
                task.get('cycle', ''),
                task.get('command', ''),
                task.get('account', ''),
                task.get('queue', ''),
                task.get('partition', ''),
                task.get('email', ''),
            ]
            
            # Add dependency information to search
            for dep in task.get('dependencies', []):
                fields_to_search.append(dep.get('target', ''))
                fields_to_search.append(dep.get('condition', ''))
                fields_to_search.append(str(dep.get('attributes', {})))
            
            # Add environment variables
            for env_var in task.get('envars', []):
                fields_to_search.append(env_var.get('name', ''))
                fields_to_search.append(env_var.get('value', ''))
            
            # Convert all fields to string and check if query is in any
            combined = ' '.join(str(field) for field in fields_to_search).lower()
            if query_lower in combined:
                results.append(task)
        
        return results
    
    @staticmethod
    def search_with_filters(tasks: List[Dict[str, Any]], 
                           query: str = "", 
                           status_filter: Optional[str] = None,
                           cycle_filter: Optional[str] = None,
                           date_range: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Search through tasks with multiple filters.
        
        Args:
            tasks: List of task dictionaries
            query: Search query string
            status_filter: Filter by status
            cycle_filter: Filter by cycle
            date_range: Filter by date range (start, end)
            
        Returns:
            List of matching task dictionaries
        """
        results = tasks
        
        # Apply status filter
        if status_filter:
            results = [task for task in results 
                      if task.get('status', '').lower() == status_filter.lower()]
        
        # Apply cycle filter
        if cycle_filter:
            results = [task for task in results 
                      if cycle_filter.lower() in task.get('cycle', '').lower()]
        
        # Apply date range filter
        if date_range:
            start_date, end_date = date_range
            filtered_results = []
            for task in results:
                start_time = task.get('start_time')
                end_time = task.get('end_time')
                
                # Check if task falls within date range
                try:
                    if start_time and start_time != 'N/A':
                        task_start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        if start_date <= task_start <= end_date:
                            filtered_results.append(task)
                            continue
                    
                    if end_time and end_time != 'N/A':
                        task_end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        if start_date <= task_end <= end_date:
                            filtered_results.append(task)
                            continue
                except:
                    # If date parsing fails, include the task anyway
                    filtered_results.append(task)
            
            results = filtered_results
        
        # Apply text search
        if query:
            results = SearchUtils.search_tasks(results, query)
        
        return results
    
    @staticmethod
    def fuzzy_search(tasks: List[Dict[str, Any]], query: str, threshold: float = 0.6) -> List[Dict[str, Any]]:
        """
        Perform fuzzy search on tasks.
        
        Args:
            tasks: List of task dictionaries
            query: Search query string
            threshold: Similarity threshold (0.0 to 1.0)
            
        Returns:
            List of matching task dictionaries with similarity scores
        """
        if not query:
            return tasks
        
        results = []
        query_lower = query.lower()
        
        for task in tasks:
            # Calculate similarity score
            similarity = SearchUtils._calculate_similarity(task, query_lower)
            
            if similarity >= threshold:
                task_copy = task.copy()
                task_copy['_search_score'] = similarity
                results.append(task_copy)
        
        # Sort by similarity score (descending)
        results.sort(key=lambda x: x.get('_search_score', 0), reverse=True)
        return results
    
    @staticmethod
    def _calculate_similarity(task: Dict[str, Any], query: str) -> float:
        """
        Calculate similarity between a task and a query string.
        
        Args:
            task: Task dictionary
            query: Query string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Extract searchable text from task
        fields_to_search = [
            task.get('id', ''),
            task.get('status', ''),
            task.get('cycle', ''),
            task.get('command', ''),
            task.get('account', ''),
            task.get('queue', ''),
            task.get('partition', ''),
            task.get('email', ''),
        ]
        
        # Add dependency information
        for dep in task.get('dependencies', []):
            fields_to_search.append(dep.get('target', ''))
            fields_to_search.append(dep.get('condition', ''))
        
        # Combine all fields
        combined = ' '.join(str(field) for field in fields_to_search).lower()
        
        # Simple word overlap approach
        query_words = set(query.split())
        text_words = set(combined.split())
        
        if not query_words:
            return 0.0
        
        overlap = len(query_words.intersection(text_words))
        total = len(query_words.union(text_words))
        
        return overlap / total if total > 0 else 0.0
    
    @staticmethod
    def search_by_regex(tasks: List[Dict[str, Any]], pattern: str) -> List[Dict[str, Any]]:
        """
        Search tasks using a regular expression pattern.
        
        Args:
            tasks: List of task dictionaries
            pattern: Regular expression pattern
            
        Returns:
            List of matching task dictionaries
        """
        try:
            compiled_pattern = re.compile(pattern, re.IGNORECASE)
        except re.error:
            # If regex is invalid, return empty results
            return []
        
        results = []
        
        for task in tasks:
            # Search in relevant fields
            fields_to_search = [
                task.get('id', ''),
                task.get('status', ''),
                task.get('cycle', ''),
                task.get('command', ''),
                task.get('account', ''),
                task.get('queue', ''),
                task.get('partition', ''),
                task.get('email', ''),
            ]
            
            # Add dependency information
            for dep in task.get('dependencies', []):
                fields_to_search.append(dep.get('target', ''))
                fields_to_search.append(dep.get('condition', ''))
            
            # Check if pattern matches any field
            combined = ' '.join(str(field) for field in fields_to_search)
            if compiled_pattern.search(combined):
                results.append(task)
        
        return results


# Create a singleton instance for convenience
search_utils = SearchUtils()