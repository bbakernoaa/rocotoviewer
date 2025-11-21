"""
Task parser module for RocotoViewer.

This module parses individual task definitions from workflow files
with backward compatibility for legacy formats.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List
import logging

from .base_parser import BaseParser


class TaskParser(BaseParser):
    """
    Parser for individual task definitions within workflow files
    with backward compatibility for legacy formats.
    """
    
    def __init__(self, config=None):
        """
        Initialize the task parser.
        
        Args:
            config: Application configuration
        """
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Legacy format compatibility mapping
        self.legacy_field_mappings = {
            'jobname': 'name',
            'jobid': 'id',
            'taskname': 'name',
            'taskid': 'id',
            'taskdef': 'task',
            'jobdef': 'task'
        }
        
        # Legacy status mappings
        self.legacy_status_mappings = {
            'S': 'SUCCESS',
            'F': 'FAILED',
            'R': 'RUNNING',
            'Q': 'QUEUED',
            'H': 'HELD',
            'U': 'UNKNOWN',
            'succeeded': 'SUCCESS',
            'failed': 'FAILED',
            'running': 'RUNNING',
            'queued': 'QUEUED',
            'held': 'HELD',
            'unknown': 'UNKNOWN'
        }
    
    def parse(self, source: str) -> Dict[str, Any]:
        """
        Parse task definitions from a source with backward compatibility.
        
        Args:
            source: Path to workflow file or XML string containing tasks
            
        Returns:
            Dictionary with parsed task data
        """
        if self._is_xml_content(source):
            # Source is XML content, parse directly
            try:
                root = ET.fromstring(source)
                # Since it's content, we can't detect format from file path
                format_info = {'version': 'unknown', 'source_type': 'content'}
                return self._parse_tasks_from_element(root, format_info)
            except ET.ParseError as e:
                self.logger.error(f"XML parsing error: {str(e)}")
                return {}
        
        # Detect format version for backward compatibility from file path
        format_info = self.detect_format_version(source)
        self.logger.info(f"Detected format: {format_info}")

        # Source is a file path
        if not self.validate_source(source):
            return {}
        
        content = self.read_file(source)
        if content is None:
            return {}
        
        try:
            root = ET.fromstring(content)
            return self._parse_tasks_from_element(root, format_info)
        except ET.ParseError as e:
            self.logger.error(f"XML parsing error in {source}: {str(e)}")
            
            # Try legacy parsing as fallback
            try:
                root = ET.fromstring(content)
                return self._parse_legacy_tasks_from_element(root, format_info)
            except:
                return {}
    
    def _is_xml_content(self, source: str) -> bool:
        """
        Check if the source is XML content rather than a file path.
        
        Args:
            source: String to check
            
        Returns:
            True if it looks like XML content, False if it looks like a file path
        """
        # Check if source contains XML tags
        return source.strip().startswith('<') and len(source) < 1000  # Arbitrary length limit
    
    def _parse_tasks_from_element(self, root: ET.Element, format_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse task definitions from an XML element with current format support.
        
        Args:
            root: Root XML element to parse
            format_info: Format detection information
            
        Returns:
            Dictionary with parsed task data
        """
        tasks = []
        
        # Look for tasks in various possible structures
        task_elements = self._find_task_elements(root)
        
        for task_elem in task_elements:
            task_data = self._extract_task_data(task_elem)
            if task_data:
                tasks.append(task_data)
        
        return {
            'tasks': tasks,
            'total_tasks': len(tasks),
            'format_info': format_info,
            'parsed_at': self._get_current_timestamp()
        }
    
    def _parse_legacy_tasks_from_element(self, root: ET.Element, format_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse task definitions from an XML element with legacy format support.
        
        Args:
            root: Root XML element to parse
            format_info: Format detection information
            
        Returns:
            Dictionary with parsed task data
        """
        tasks = []
        
        # Look for tasks in various possible structures including legacy formats
        task_elements = self._find_legacy_task_elements(root)
        
        for task_elem in task_elements:
            task_data = self._extract_legacy_task_data(task_elem)
            if task_data:
                tasks.append(task_data)
        
        # Apply legacy format transformations
        result = {
            'tasks': tasks,
            'total_tasks': len(tasks),
            'format_info': format_info,
            'parsed_at': self._get_current_timestamp()
        }
        
        return self.handle_legacy_format(result, format_info)
    
    def _find_task_elements(self, root: ET.Element) -> List[ET.Element]:
        """
        Find all task elements in the XML structure for current format.
        
        Args:
            root: Root XML element
            
        Returns:
            List of task XML elements
        """
        task_elements = []
        
        # Look for tasks in various possible locations
        # Check if the root element itself is a task
        if root.tag.lower() in ['task', 'taskdef', 'node']:
            task_elements.append(root)

        # Standard Rocoto structure
        tasks_section = root.find('tasks')
        if tasks_section is not None:
            for child in tasks_section:
                if child.tag.lower() in ['task', 'taskdef', 'node']:
                    task_elements.append(child)
        
        # If no tasks found in tasks section, look directly in root
        if not task_elements:
            for child in root:
                if child.tag.lower() in ['task', 'taskdef', 'node']:
                    task_elements.append(child)
        
        # Look for tasks in other possible structures
        if not task_elements:
            # Search recursively for task elements
            task_elements = root.findall('.//task') + root.findall('.//taskdef') + root.findall('.//node')
        
        return task_elements
    
    def _find_legacy_task_elements(self, root: ET.Element) -> List[ET.Element]:
        """
        Find all task elements in the XML structure for legacy format.
        
        Args:
            root: Root XML element
            
        Returns:
            List of task XML elements
        """
        task_elements = []
        
        # Look for tasks in various possible locations including legacy formats
        # Standard Rocoto structure
        for tag in ['tasks', 'taskdefs', 'tasklist', 'jobs', 'jobdefs']:
            tasks_section = root.find(tag)
            if tasks_section is not None:
                for child in tasks_section:
                    if child.tag.lower() in ['task', 'taskdef', 'node', 'job', 'jobdef']:
                        task_elements.append(child)
        
        # If no tasks found in tasks section, look directly in root
        if not task_elements:
            for child in root:
                if child.tag.lower() in ['task', 'taskdef', 'node', 'job', 'jobdef']:
                    task_elements.append(child)
        
        # Look for tasks in other possible structures
        if not task_elements:
            # Search recursively for task elements including legacy formats
            task_elements = (root.findall('.//task') + 
                           root.findall('.//taskdef') + 
                           root.findall('.//node') +
                           root.findall('.//job') +
                           root.findall('.//jobdef'))
        
        return task_elements
    
    def _extract_task_data(self, task_elem: ET.Element) -> Dict[str, Any]:
        """
        Extract data from a single task XML element in current format.
        
        Args:
            task_elem: XML element representing a task
            
        Returns:
            Dictionary with task data
        """
        task_data = {
            'id': task_elem.get('name', task_elem.get('id', '')),
            'type': task_elem.tag,
            'status': task_elem.get('status', 'unknown'),
            'native': {},
            'command': '',
            'envars': [],
            'dependency': {},
            'attributes': {},
            'metatasks': []
        }
        
        # Extract all attributes
        for attr_name, attr_value in task_elem.attrib.items():
            task_data['attributes'][attr_name] = attr_value
        
        # Parse child elements
        for child in task_elem:
            tag_lower = child.tag.lower()
            
            if tag_lower in ['command', 'cmd']:
                task_data['command'] = child.text or ''
            elif tag_lower == 'envar':
                envar = {
                    'name': child.get('name', ''),
                    'value': child.get('value', child.text or '')
                }
                task_data['envars'].append(envar)
            elif tag_lower in ['dependency', 'depends', 'prereq']:
                task_data['dependency'] = self._parse_dependency(child)
            elif tag_lower == 'metatask':
                metatask = {
                    'name': child.get('name', ''),
                    'attributes': dict(child.attrib),
                    'tasks': []
                }
                
                # Parse tasks within metatask
                for subchild in child:
                    if subchild.tag.lower() in ['task', 'taskdef']:
                        subtask_data = self._extract_task_data(subchild)
                        metatask['tasks'].append(subtask_data)
                
                task_data['metatasks'].append(metatask)
            elif tag_lower == 'cyclestr':
                task_data['cycle_string'] = child.text or ''
            elif tag_lower == 'account':
                task_data['account'] = child.text or ''
            elif tag_lower == 'native':
                # Handle native SLURM/PBS directives
                task_data['native'][child.tag] = dict(child.attrib)
                if child.text:
                    task_data['native'][child.tag]['text'] = child.text
    
        return task_data
    
    def _extract_legacy_task_data(self, task_elem: ET.Element) -> Dict[str, Any]:
        """
        Extract data from a single task XML element in legacy format.
        
        Args:
            task_elem: XML element representing a task
            
        Returns:
            Dictionary with task data
        """
        # Start with standard task data
        task_data = self._extract_task_data(task_elem)
        
        # Apply legacy-specific mappings and transformations
        for legacy_attr, current_attr in self.legacy_field_mappings.items():
            if task_elem.get(legacy_attr) and not task_data.get(current_attr):
                task_data[current_attr] = task_elem.get(legacy_attr)
        
        # Transform legacy status values
        if task_data.get('status') in self.legacy_status_mappings:
            task_data['status'] = self.legacy_status_mappings[task_data['status']]
        
        # Handle legacy element structures
        for child in task_elem:
            tag_lower = child.tag.lower()
            
            if tag_lower == 'jobname':
                # Legacy job name field
                if not task_data.get('name'):
                    task_data['name'] = child.text or ''
            elif tag_lower == 'jobid':
                # Legacy job ID field
                if not task_data.get('id'):
                    task_data['id'] = child.text or ''
            elif tag_lower in ['dependency', 'depends', 'prereq', 'statisfied']:
                task_data['dependency'] = self._parse_dependency(child)
            elif tag_lower == 'var':
                # Handle variables (legacy format)
                envar = {
                    'name': child.get('name', ''),
                    'value': child.text or ''
                }
                task_data['envars'].append(envar)
            elif tag_lower == 'command':
                # Handle command
                task_data['command'] = child.text or ''
        
        return task_data
    
    def _parse_dependency(self, dep_elem: ET.Element) -> Dict[str, Any]:
        """
        Parse dependency element.
        
        Args:
            dep_elem: XML element representing a dependency
            
        Returns:
            Dictionary with dependency data
        """
        dependency = {
            'type': dep_elem.tag,
            'attributes': dict(dep_elem.attrib),
            'condition': dep_elem.text or '',
            'tasks': [],
            'data': {}
        }
        
        # Parse nested dependency elements
        for child in dep_elem:
            if child.tag.lower() in ['taskdep', 'datadep', 'streq', 'and', 'or']:
                child_dep = {
                    'type': child.tag,
                    'attributes': dict(child.attrib),
                    'condition': child.text or ''
                }
                dependency['tasks'].append(child_dep)
        
        return dependency
    
    def _get_current_timestamp(self) -> str:
        """
        Get the current timestamp in ISO format.
        
        Returns:
            Current timestamp as ISO string
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def validate_task_data(self, task_data: Dict[str, Any]) -> bool:
        """
        Validate parsed task data.
        
        Args:
            task_data: Parsed task data to validate
            
        Returns:
            True if task data is valid, False otherwise
        """
        if not task_data:
            return False
        
        # Check for required fields in each task
        if 'tasks' in task_data:
            for task in task_data['tasks']:
                if not isinstance(task, dict) or 'id' not in task:
                    self.logger.warning("Task missing required 'id' field")
                    return False
        
        return True
    
    def get_task_summary(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a summary of parsed task data with backward compatibility.
        
        Args:
            task_data: Parsed task data from parse() method
            
        Returns:
            Summary dictionary
        """
        if not task_data or 'tasks' not in task_data:
            return {}
        
        tasks = task_data['tasks']
        
        # Count task types
        type_counts = {}
        status_counts = {}
        
        for task in tasks:
            task_type = task.get('type', 'unknown')
            type_counts[task_type] = type_counts.get(task_type, 0) + 1
            
            status = task.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Check for tasks with dependencies
        tasks_with_deps = sum(1 for task in tasks if task.get('dependency'))
        
        return {
            'total_tasks': len(tasks),
            'type_counts': type_counts,
            'status_counts': status_counts,
            'tasks_with_dependencies': tasks_with_deps,
            'tasks_without_dependencies': len(tasks) - tasks_with_deps,
            'format_info': task_data.get('format_info', {})
        }