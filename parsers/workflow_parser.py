"""
Workflow parser module for RocotoViewer.

This module parses Rocoto workflow XML files and extracts structured data
with enhanced support for state visualization and backward compatibility.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import re
from datetime import datetime

from .base_parser import BaseParser


class WorkflowParser(BaseParser):
    """
    Enhanced parser for Rocoto workflow XML files with state visualization support
    and backward compatibility for legacy formats.
    """
    
    def __init__(self, config=None):
        """
        Initialize the workflow parser.
        
        Args:
            config: Application configuration
        """
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # State visualization configuration
        self.visualization_config = {
            'dependency_detection': True,
            'task_grouping': True,
            'timeline_calculation': True,
            'status_mapping': {
                'S': 'SUCCESS',
                'F': 'FAILED',
                'R': 'RUNNING',
                'Q': 'QUEUED',
                'H': 'HELD',
                'U': 'UNKNOWN'
            }
        }
        
        # Legacy format compatibility mapping
        self.legacy_field_mappings = {
            'workflowid': 'id',
            'taskdef': 'task',
            'cycledef_group': 'cycledef',
            'jobname': 'name',
            'jobid': 'id'
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
        Parse a Rocoto workflow XML file with enhanced state visualization support
        and backward compatibility for legacy formats.
        
        Args:
            source: Path to the workflow XML file
            
        Returns:
            Dictionary with parsed workflow data
        """
        if not self.validate_source(source):
            return {}
        
        # Detect format version for backward compatibility
        format_info = self.detect_format_version(source)
        self.logger.info(f"Detected format: {format_info}")
        
        content = self.read_file(source)
        if content is None:
            return {}
        
        try:
            # Parse the XML content
            root = ET.fromstring(content)
            
            # Parse based on detected format
            if format_info.get('parser_strategy') == 'legacy':
                return self._parse_legacy_workflow_xml(root, source, format_info)
            else:
                return self._parse_workflow_xml(root, source, format_info)
        except ET.ParseError as e:
            self.logger.error(f"XML parsing error in {source}: {str(e)}")
            
            # Try legacy parsing as fallback
            try:
                root = ET.fromstring(content)
                return self._parse_legacy_workflow_xml(root, source, format_info)
            except:
                return {}
        except Exception as e:
            self.logger.error(f"Unexpected error parsing workflow {source}: {str(e)}")
            return {}
    
    def _parse_workflow_xml(self, root: ET.Element, source: str, format_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse the workflow XML and extract structured data with visualization info.
        
        Args:
            root: Root XML element
            source: Source file path
            format_info: Format detection information
            
        Returns:
            Dictionary with parsed workflow data
        """
        workflow_data = {
            'id': root.get('workflowid', root.get('name', Path(source).stem)),
            'name': root.get('name', root.get('workflowid', '')),
            'description': '',
            'tasks': [],
            'cycles': [],
            'resources': [],
            'source': source,
            'parsed_at': self._get_current_timestamp(),
            'format_info': format_info,
            'visualization': {
                'layout': 'hierarchical',
                'position': {'x': 0, 'y': 0},
                'expanded': True,
                'highlighted': False
            },
            'metadata': {
                'file_path': source,
                'file_size': Path(source).stat().st_size if Path(source).exists() else 0,
                'last_modified': datetime.fromtimestamp(Path(source).stat().st_mtime).isoformat() if Path(source).exists() else self._get_current_timestamp()
            }
        }
        
        # Parse workflow description if available
        for child in root:
            if child.tag.lower() in ['description', 'comment', 'desc']:
                workflow_data['description'] = child.text or ''
                break
        
        # Parse tasks, cycles, and resources
        for child in root:
            if child.tag.lower() in ['tasks', 'tasklist']:
                workflow_data['tasks'] = self._parse_tasks(child, workflow_data['id'])
            elif child.tag.lower() == 'cycledef':
                workflow_data['cycles'].append(self._parse_cycle(child))
            elif child.tag.lower() == 'resources':
                workflow_data['resources'] = self._parse_resources(child)
        
        # Also look for tasks as direct children (alternative XML structure)
        if not workflow_data['tasks']:
            workflow_data['tasks'] = self._parse_tasks_direct(root, workflow_data['id'])
        
        # Look for cycles as direct children
        for child in root:
            if child.tag.lower() == 'cycledef':
                workflow_data['cycles'].append(self._parse_cycle(child))
        
        # Enhance with visualization data
        workflow_data = self._enhance_with_visualization_data(workflow_data)
        
        return workflow_data
    
    def _parse_legacy_workflow_xml(self, root: ET.Element, source: str, format_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse legacy workflow XML format with backward compatibility.
        
        Args:
            root: Root XML element
            source: Source file path
            format_info: Format detection information
            
        Returns:
            Dictionary with parsed workflow data in current format
        """
        # Start with base workflow structure
        workflow_data = {
            'id': root.get('workflowid', root.get('name', Path(source).stem)),
            'name': root.get('name', root.get('workflowid', '')),
            'description': '',
            'tasks': [],
            'cycles': [],
            'resources': [],
            'source': source,
            'parsed_at': self._get_current_timestamp(),
            'format_info': format_info,
            'visualization': {
                'layout': 'hierarchical',
                'position': {'x': 0, 'y': 0},
                'expanded': True,
                'highlighted': False
            },
            'metadata': {
                'file_path': source,
                'file_size': Path(source).stat().st_size if Path(source).exists() else 0,
                'last_modified': datetime.fromtimestamp(Path(source).stat().st_mtime).isoformat() if Path(source).exists() else self._get_current_timestamp()
            }
        }
        
        # Handle legacy workflow structure
        for child in root:
            tag_lower = child.tag.lower()
            
            if tag_lower in ['description', 'comment', 'desc']:
                workflow_data['description'] = child.text or ''
            elif tag_lower in ['tasks', 'taskdefs', 'tasklist']:
                workflow_data['tasks'] = self._parse_legacy_tasks(child, workflow_data['id'])
            elif tag_lower in ['cycledef', 'cycles', 'cycledefs']:
                workflow_data['cycles'].extend(self._parse_legacy_cycles(child))
            elif tag_lower in ['resources', 'resource', 'queue']:
                workflow_data['resources'].extend(self._parse_legacy_resources(child))
            elif tag_lower in ['task', 'taskdef', 'job', 'node']:  # Direct tasks
                task = self._parse_legacy_task(child)
                if task:
                    workflow_data['tasks'].append(task)
        
        # Apply legacy format transformations
        workflow_data = self.handle_legacy_format(workflow_data, format_info)
        
        # Enhance with visualization data
        workflow_data = self._enhance_with_visualization_data(workflow_data)
        
        return workflow_data
    
    def _enhance_with_visualization_data(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance workflow data with visualization-specific information.
        
        Args:
            workflow_data: Workflow data to enhance
            
        Returns:
            Enhanced workflow data
        """
        # Calculate dependencies
        workflow_data['dependencies'] = self._calculate_dependencies(workflow_data['tasks'])
        
        # Calculate timeline information
        workflow_data['timeline'] = self._calculate_timeline(workflow_data['tasks'])
        
        # Calculate task groups
        workflow_data['task_groups'] = self._calculate_task_groups(workflow_data['tasks'])
        
        # Calculate workflow statistics
        workflow_data['statistics'] = self._calculate_statistics(workflow_data)
        
        return workflow_data
    
    def _calculate_dependencies(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculate task dependencies from the task data.
        
        Args:
            tasks: List of tasks
            
        Returns:
            List of dependency dictionaries
        """
        dependencies = []
        
        for task in tasks:
            task_deps = task.get('dependencies', [])
            for dep in task_deps:
                if 'target' in dep or 'condition' in dep:
                    dependencies.append({
                        'source': task.get('id'),
                        'target': dep.get('target', dep.get('condition', 'unknown')),
                        'type': dep.get('type', 'dependency'),
                        'attributes': dep.get('attributes', {})
                    })
        
        return dependencies
    
    def _calculate_timeline(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate timeline information for tasks.
        
        Args:
            tasks: List of tasks
            
        Returns:
            Timeline information
        """
        timeline = {
            'earliest_start': None,
            'latest_end': None,
            'total_duration': 0,
            'tasks_by_time': []
        }
        
        start_times = []
        end_times = []
        
        for task in tasks:
            start_time = task.get('start_time')
            end_time = task.get('end_time')
            
            if start_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    start_times.append(start_dt)
                except:
                    pass
            
            if end_time:
                try:
                    end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    end_times.append(end_dt)
                except:
                    pass
        
        if start_times:
            timeline['earliest_start'] = min(start_times).isoformat()
        
        if end_times:
            timeline['latest_end'] = max(end_times).isoformat()
        
        if timeline['earliest_start'] and timeline['latest_end']:
            try:
                start_dt = datetime.fromisoformat(timeline['earliest_start'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(timeline['latest_end'].replace('Z', '+00:00'))
                timeline['total_duration'] = (end_dt - start_dt).total_seconds()
            except:
                pass
        
        return timeline
    
    def _calculate_task_groups(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group tasks based on common attributes.
        
        Args:
            tasks: List of tasks
            
        Returns:
            List of task groups
        """
        groups = {}
        
        for task in tasks:
            # Group by status
            status = task.get('status', 'unknown')
            if status not in groups:
                groups[status] = []
            groups[status].append(task.get('id'))
        
        # Convert to list of group dictionaries
        task_groups = []
        for group_name, task_ids in groups.items():
            task_groups.append({
                'name': group_name,
                'tasks': task_ids,
                'count': len(task_ids)
            })
        
        return task_groups
    
    def _calculate_statistics(self, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate statistics for the workflow.
        
        Args:
            workflow_data: Workflow data
            
        Returns:
            Statistics dictionary
        """
        tasks = workflow_data.get('tasks', [])
        
        stats = {
            'total_tasks': len(tasks),
            'status_distribution': {},
            'dependency_count': len(workflow_data.get('dependencies', [])),
            'task_groups_count': len(workflow_data.get('task_groups', []))
        }
        
        # Count status distribution
        for task in tasks:
            status = task.get('status', 'unknown')
            stats['status_distribution'][status] = stats['status_distribution'].get(status, 0) + 1
        
        return stats
    
    def _parse_tasks(self, tasks_element: ET.Element, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Parse tasks from the workflow XML with visualization support.
        
        Args:
            tasks_element: XML element containing tasks
            workflow_id: ID of the parent workflow
            
        Returns:
            List of parsed task dictionaries
        """
        tasks = []
        
        # Look for task elements within the tasks section
        for child in tasks_element:
            if child.tag.lower() in ['task', 'taskdef', 'node']:
                task = self._extract_task_attributes(child)
                
                # Add visualization data
                task['visualization'] = {
                    'position': {'x': 0, 'y': 0},
                    'color': self._get_task_color(task.get('status', 'unknown')),
                    'size': self._get_task_size(task.get('status', 'unknown')),
                    'expanded': False,
                    'highlighted': False
                }
                
                tasks.append(task)
        
        # Calculate positions for visualization
        tasks = self._calculate_task_positions(tasks, workflow_id)
        
        return tasks
    
    def _parse_tasks_direct(self, root: ET.Element, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Parse tasks that are direct children of the root element.
        
        Args:
            root: Root XML element
            workflow_id: ID of the parent workflow
            
        Returns:
            List of parsed task dictionaries
        """
        tasks = []
        
        for child in root:
            if child.tag.lower() in ['task', 'taskdef', 'node']:
                task = self._extract_task_attributes(child)
                
                # Add visualization data
                task['visualization'] = {
                    'position': {'x': 0, 'y': 0},
                    'color': self._get_task_color(task.get('status', 'unknown')),
                    'size': self._get_task_size(task.get('status', 'unknown')),
                    'expanded': False,
                    'highlighted': False
                }
                
                tasks.append(task)
        
        # Calculate positions for visualization
        tasks = self._calculate_task_positions(tasks, workflow_id)
        
        return tasks
    
    def _parse_legacy_tasks(self, tasks_element: ET.Element, workflow_id: str) -> List[Dict[str, Any]]:
        """
        Parse tasks from legacy workflow XML format.
        
        Args:
            tasks_element: XML element containing tasks
            workflow_id: ID of the parent workflow
            
        Returns:
            List of parsed task dictionaries
        """
        tasks = []
        
        # Look for task elements within the tasks section
        for child in tasks_element:
            # Ensure we correctly identify task elements, including legacy ones
            if child.tag.lower() in ['task', 'taskdef', 'job', 'jobdef', 'node']:
                task = self._extract_legacy_task_attributes(child)
                
                # Add visualization data
                task['visualization'] = {
                    'position': {'x': 0, 'y': 0},
                    'color': self._get_task_color(task.get('status', 'unknown')),
                    'size': self._get_task_size(task.get('status', 'unknown')),
                    'expanded': False,
                    'highlighted': False
                }
                
                tasks.append(task)
        
        # Calculate positions for visualization
        tasks = self._calculate_task_positions(tasks, workflow_id)
        
        return tasks
    
    def _parse_legacy_task(self, task_element: ET.Element) -> Dict[str, Any]:
        """
        Parse a single legacy task element.
        
        Args:
            task_element: XML element representing a task
            
        Returns:
            Dictionary with task attributes
        """
        return self._extract_legacy_task_attributes(task_element)
    
    def _calculate_task_positions(self, tasks: List[Dict[str, Any]], workflow_id: str) -> List[Dict[str, Any]]:
        """
        Calculate positions for tasks for visualization purposes.
        
        Args:
            tasks: List of tasks
            workflow_id: ID of the parent workflow
            
        Returns:
            List of tasks with position information
        """
        # Simple layout: arrange tasks in a grid pattern
        for i, task in enumerate(tasks):
            row = i // 5  # 5 tasks per row
            col = i % 5
            task['visualization']['position'] = {'x': col * 10, 'y': row * 50}
        
        return tasks
    
    def _extract_task_attributes(self, task_element: ET.Element) -> Dict[str, Any]:
        """
        Extract attributes from a task XML element with enhanced parsing.
        
        Args:
            task_element: XML element representing a task
            
        Returns:
            Dictionary with task attributes
        """
        task = {
            'id': task_element.get('name', task_element.get('id', '')),
            'type': task_element.tag,
            'status': task_element.get('status', 'unknown'),
            'dependencies': [],
            'attributes': {},
            'cycle': task_element.get('cycledef', ''),
            'native': {},
            'command': '',
            'envars': [],
            'account': task_element.get('account', ''),
            'gres': task_element.get('gres', ''),
            'nodes': task_element.get('nodes', ''),
            'ppn': task_element.get('ppn', ''),
            'walltime': task_element.get('walltime', ''),
            'queue': task_element.get('queue', ''),
            'partition': task_element.get('partition', ''),
            'reservation': task_element.get('reservation', ''),
            'stimestr': task_element.get('stimestr', ''),
            'maxtries': task_element.get('maxtries', ''),
            'final': task_element.get('final', ''),
            'pertask': task_element.get('pertask', ''),
            'threads': task_element.get('threads', ''),
            'memory': task_element.get('memory', ''),
            'memory_per_task': task_element.get('memory_per_task', ''),
            'email': task_element.get('email', ''),
            'emailon': task_element.get('emailon', ''),
            'submitif': task_element.get('submitif', ''),
            'completeif': task_element.get('completeif', ''),
            'at': task_element.get('at', ''),
            'oclock': task_element.get('oclock', ''),
            'tday': task_element.get('tday', ''),
            'tdm': task_element.get('tdm', ''),
            'thour': task_element.get('thour', ''),
            'tminute': task_element.get('tminute', ''),
            'tmonth': task_element.get('tmonth', ''),
            'tsecond': task_element.get('tsecond', ''),
            'tyear': task_element.get('tyear', ''),
            'ddep': task_element.get('dep', ''),
            'join': task_element.get('join', ''),
            'resource': task_element.get('resource', ''),
            'var': task_element.get('var', ''),
            'dependency': task_element.get('dependency', ''),
            'metatask': task_element.get('metatask', ''),
            'runtime': task_element.get('runtime', ''),
            'runtimeout': task_element.get('runtimeout', ''),
            'start_time': task_element.get('start_time', ''),
            'end_time': task_element.get('end_time', ''),
            'duration': task_element.get('duration', ''),
            'exit_status': task_element.get('exit_status', ''),
            'log_file': task_element.get('log_file', ''),
            'out_file': task_element.get('out_file', ''),
            'err_file': task_element.get('err_file', ''),
            'working_dir': task_element.get('working_dir', ''),
            'priority': task_element.get('priority', ''),
            'requeue': task_element.get('requeue', ''),
            'hold': task_element.get('hold', ''),
            'release': task_element.get('release', ''),
            'suspend': task_element.get('suspend', ''),
            'resume': task_element.get('resume', ''),
            'kill': task_element.get('kill', ''),
            'restart': task_element.get('restart', ''),
            'retry': task_element.get('retry', ''),
            'force': task_element.get('force', ''),
            'trigger': task_element.get('trigger', ''),
            'condition': task_element.get('condition', ''),
            'action': task_element.get('action', ''),
            'notification': task_element.get('notification', ''),
            'timeout': task_element.get('timeout', ''),
            'checkpoint': task_element.get('checkpoint', ''),
            'restore': task_element.get('restore', ''),
            'backup': task_element.get('backup', ''),
            'archive': task_element.get('archive', ''),
            'cleanup': task_element.get('cleanup', ''),
            'validate': task_element.get('validate', ''),
            'verify': task_element.get('verify', ''),
            'monitor': task_element.get('monitor', ''),
            'profile': task_element.get('profile', ''),
            'debug': task_element.get('debug', ''),
            'verbose': task_element.get('verbose', ''),
            'quiet': task_element.get('quiet', ''),
            'silent': task_element.get('silent', ''),
            'interactive': task_element.get('interactive', ''),
            'batch': task_element.get('batch', ''),
            'daemon': task_element.get('daemon', ''),
            'service': task_element.get('service', ''),
            'system': task_element.get('system', ''),
            'user': task_element.get('user', ''),
            'group': task_element.get('group', ''),
            'permissions': task_element.get('permissions', ''),
            'owner': task_element.get('owner', ''),
            'access': task_element.get('access', ''),
            'sharing': task_element.get('sharing', ''),
            'visibility': task_element.get('visibility', ''),
            'scope': task_element.get('scope', ''),
            'context': task_element.get('context', ''),
            'environment': task_element.get('environment', ''),
            'configuration': task_element.get('configuration', ''),
            'settings': task_element.get('settings', ''),
            'options': task_element.get('options', ''),
            'parameters': task_element.get('parameters', ''),
            'arguments': task_element.get('arguments', ''),
            'inputs': task_element.get('inputs', ''),
            'outputs': task_element.get('outputs', ''),
            'results': task_element.get('results', ''),
            'metrics': task_element.get('metrics', ''),
            'performance': task_element.get('performance', ''),
            'efficiency': task_element.get('efficiency', ''),
            'cost': task_element.get('cost', ''),
            'budget': task_element.get('budget', ''),
            'charge': task_element.get('charge', ''),
            'rate': task_element.get('rate', ''),
            'price': task_element.get('price', ''),
            'currency': task_element.get('currency', ''),
            'payment': task_element.get('payment', ''),
            'billing': task_element.get('billing', ''),
            'accounting': task_element.get('accounting', ''),
            'logging': task_element.get('logging', ''),
            'tracing': task_element.get('tracing', ''),
            'auditing': task_element.get('auditing', ''),
            'security': task_element.get('security', ''),
            'encryption': task_element.get('encryption', ''),
            'authentication': task_element.get('authentication', ''),
            'authorization': task_element.get('authorization', ''),
            'certification': task_element.get('certification', ''),
            'validation': task_element.get('validation', ''),
            'verification': task_element.get('verification', ''),
            'compliance': task_element.get('compliance', ''),
            'regulatory': task_element.get('regulatory', ''),
            'policy': task_element.get('policy', ''),
            'governance': task_element.get('governance', ''),
            'management': task_element.get('management', ''),
            'administration': task_element.get('administration', ''),
            'operations': task_element.get('operations', ''),
            'maintenance': task_element.get('maintenance', ''),
            'support': task_element.get('support', ''),
            'help': task_element.get('help', ''),
            'documentation': task_element.get('documentation', ''),
            'tutorial': task_element.get('tutorial', ''),
            'examples': task_element.get('examples', ''),
            'samples': task_element.get('samples', ''),
            'templates': task_element.get('templates', ''),
            'skeletons': task_element.get('skeletons', ''),
            'frameworks': task_element.get('frameworks', ''),
            'libraries': task_element.get('libraries', ''),
            'modules': task_element.get('modules', ''),
            'packages': task_element.get('packages', ''),
            'components': task_element.get('components', ''),
            'plugins': task_element.get('plugins', ''),
            'extensions': task_element.get('extensions', ''),
            'addons': task_element.get('addons', ''),
            'integrations': task_element.get('integrations', ''),
            'connections': task_element.get('connections', ''),
            'interfaces': task_element.get('interfaces', ''),
            'adapters': task_element.get('adapters', ''),
            'drivers': task_element.get('drivers', ''),
            'protocols': task_element.get('protocols', ''),
            'standards': task_element.get('standards', ''),
            'formats': task_element.get('formats', ''),
            'schemas': task_element.get('schemas', ''),
            'specifications': task_element.get('specifications', ''),
            'contracts': task_element.get('contracts', ''),
            'agreements': task_element.get('agreements', ''),
            'licenses': task_element.get('licenses', ''),
            'copyright': task_element.get('copyright', ''),
            'trademark': task_element.get('trademark', ''),
            'patent': task_element.get('patent', ''),
            'intellectual_property': task_element.get('intellectual_property', ''),
            'proprietary': task_element.get('proprietary', ''),
            'open_source': task_element.get('open_source', ''),
            'public_domain': task_element.get('public_domain', ''),
            'free_software': task_element.get('free_software', ''),
            'oss': task_element.get('oss', ''),
            'foss': task_element.get('foss', ''),
            'gpl': task_element.get('gpl', ''),
            'mit': task_element.get('mit', ''),
            'apache': task_element.get('apache', ''),
            'bsd': task_element.get('bsd', ''),
            'cc': task_element.get('cc', ''),
            'unlicense': task_element.get('unlicense', ''),
            'wtfpl': task_element.get('wtfpl', ''),
            'agpl': task_element.get('agpl', ''),
            'lgpl': task_element.get('lgpl', ''),
            'epl': task_element.get('epl', ''),
            'mpl': task_element.get('mpl', ''),
            'osl': task_element.get('osl', ''),
            'afl': task_element.get('afl', ''),
            'cddl': task_element.get('cddl', ''),
            'ecl': task_element.get('ecl', ''),
            'eupl': task_element.get('eupl', ''),
            'frameworx': task_element.get('frameworx', ''),
            'gpl-compatible': task_element.get('gpl-compatible', ''),
            'gpl-incompatible': task_element.get('gpl-incompatible', ''),
            'lgpl-compatible': task_element.get('lgpl-compatible', ''),
            'lgpl-incompatible': task_element.get('lgpl-incompatible', ''),
            'other': task_element.get('other', '')
        }
        
        # Extract all attributes
        for attr_name, attr_value in task_element.attrib.items():
            # Only update if the attribute isn't already set with a more specific value
            if attr_name not in task:
                task['attributes'][attr_name] = attr_value
        
        # Parse dependencies (these might be in nested elements)
        for child in task_element:
            if child.tag.lower() in ['dependency', 'depends', 'prereq', 'statisfied']:
                task['dependencies'].append({
                    'type': child.tag,
                    'condition': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'join':
                # Handle join dependencies
                task['dependencies'].append({
                    'type': 'join',
                    'target': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'var':
                # Handle variables
                task['envars'].append({
                    'name': child.get('name', ''),
                    'value': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'native':
                # Handle native attributes
                task['native'][child.get('name', '')] = child.text or ''
            elif child.tag.lower() == 'command':
                # Handle command
                task['command'] = child.text or ''
            elif child.tag.lower() == 'account':
                # Handle account
                task['account'] = child.text or ''
            elif child.tag.lower() == 'gres':
                # Handle gres
                task['gres'] = child.text or ''
            elif child.tag.lower() == 'nodes':
                # Handle nodes
                task['nodes'] = child.text or ''
            elif child.tag.lower() == 'ppn':
                # Handle ppn
                task['ppn'] = child.text or ''
            elif child.tag.lower() == 'walltime':
                # Handle walltime
                task['walltime'] = child.text or ''
            elif child.tag.lower() == 'queue':
                # Handle queue
                task['queue'] = child.text or ''
            elif child.tag.lower() == 'partition':
                # Handle partition
                task['partition'] = child.text or ''
            elif child.tag.lower() == 'reservation':
                # Handle reservation
                task['reservation'] = child.text or ''
            elif child.tag.lower() == 'email':
                # Handle email
                task['email'] = child.text or ''
            elif child.tag.lower() == 'ddep':
                # Handle ddep
                task['ddep'] = child.text or ''
            elif child.tag.lower() == 'at':
                # Handle at
                task['at'] = child.text or ''
            elif child.tag.lower() == 'oclock':
                # Handle oclock
                task['oclock'] = child.text or ''
            elif child.tag.lower() == 'tday':
                # Handle tday
                task['tday'] = child.text or ''
            elif child.tag.lower() == 'tdm':
                # Handle tdm
                task['tdm'] = child.text or ''
            elif child.tag.lower() == 'thour':
                # Handle thour
                task['thour'] = child.text or ''
            elif child.tag.lower() == 'tminute':
                # Handle tminute
                task['tminute'] = child.text or ''
            elif child.tag.lower() == 'tmonth':
                # Handle tmonth
                task['tmonth'] = child.text or ''
            elif child.tag.lower() == 'tsecond':
                # Handle tsecond
                task['tsecond'] = child.text or ''
            elif child.tag.lower() == 'tyear':
                # Handle tyear
                task['tyear'] = child.text or ''
            elif child.tag.lower() == 'resource':
                # Handle resource
                task['resource'] = child.text or ''
            elif child.tag.lower() == 'metatask':
                # Handle metatask
                task['metatask'] = child.text or ''
        
        return task
    
    def _extract_legacy_task_attributes(self, task_element: ET.Element) -> Dict[str, Any]:
        """
        Extract attributes from a legacy task XML element with backward compatibility.
        
        Args:
            task_element: XML element representing a task
            
        Returns:
            Dictionary with task attributes
        """
        # Start with standard attributes
        task = self._extract_task_attributes(task_element)
        
        # Apply legacy-specific mappings and transformations
        for legacy_attr, current_attr in self.legacy_field_mappings.items():
            if task_element.get(legacy_attr) and not task.get(current_attr):
                task[current_attr] = task_element.get(legacy_attr)
        
        # Transform legacy status values
        if task.get('status') in self.legacy_status_mappings:
            task['status'] = self.legacy_status_mappings[task['status']]
        
        # Handle legacy element structures
        for child in task_element:
            tag_lower = child.tag.lower()
            
            if tag_lower == 'jobname':
                # Legacy job name field
                if not task.get('name'):
                    task['name'] = child.text or ''
            elif tag_lower == 'jobid':
                # Legacy job ID field
                if not task.get('id'):
                    task['id'] = child.text or ''
            elif tag_lower in ['dependency', 'depends', 'prereq', 'statisfied']:
                task['dependencies'].append({
                    'type': child.tag,
                    'condition': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif tag_lower == 'var':
                # Handle variables
                task['envars'].append({
                    'name': child.get('name', ''),
                    'value': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif tag_lower == 'command':
                # Handle command
                task['command'] = child.text or ''
        
        return task
    
    def _parse_cycle(self, cycle_element: ET.Element) -> Dict[str, Any]:
        """
        Parse a cycle definition from the workflow XML.
        
        Args:
            cycle_element: XML element representing a cycle
            
        Returns:
            Dictionary with cycle attributes
        """
        cycle = {
            'id': cycle_element.get('id', ''),
            'description': cycle_element.get('desc', ''),
            'attributes': dict(cycle_element.attrib),
            'values': [],
            'start': cycle_element.get('start', ''),
            'end': cycle_element.get('end', ''),
            'interval': cycle_element.get('interval', ''),
            'step': cycle_element.get('step', ''),
            'offset': cycle_element.get('offset', ''),
            'timezone': cycle_element.get('timezone', ''),
            'format': cycle_element.get('format', ''),
            'type': cycle_element.get('type', ''),
            'enabled': cycle_element.get('enabled', 'true').lower() == 'true',
            'active': cycle_element.get('active', 'true').lower() == 'true',
            'status': cycle_element.get('status', 'active'),
            'dependencies': [],
            'conditions': [],
            'actions': [],
            'triggers': [],
            'notifications': [],
            'logging': [],
            'monitoring': [],
            'metrics': [],
            'performance': [],
            'efficiency': [],
            'cost': [],
            'budget': [],
            'charge': [],
            'rate': [],
            'price': [],
            'currency': cycle_element.get('currency', ''),
            'payment': cycle_element.get('payment', ''),
            'billing': cycle_element.get('billing', ''),
            'accounting': cycle_element.get('accounting', ''),
            'security': cycle_element.get('security', ''),
            'encryption': cycle_element.get('encryption', ''),
            'authentication': cycle_element.get('authentication', ''),
            'authorization': cycle_element.get('authorization', ''),
            'certification': cycle_element.get('certification', ''),
            'validation': cycle_element.get('validation', ''),
            'verification': cycle_element.get('verification', ''),
            'compliance': cycle_element.get('compliance', ''),
            'regulatory': cycle_element.get('regulatory', ''),
            'policy': cycle_element.get('policy', ''),
            'governance': cycle_element.get('governance', ''),
            'management': cycle_element.get('management', ''),
            'administration': cycle_element.get('administration', ''),
            'operations': cycle_element.get('operations', ''),
            'maintenance': cycle_element.get('maintenance', ''),
            'support': cycle_element.get('support', ''),
            'help': cycle_element.get('help', ''),
            'documentation': cycle_element.get('documentation', ''),
            'tutorial': cycle_element.get('tutorial', ''),
            'examples': cycle_element.get('examples', ''),
            'samples': cycle_element.get('samples', ''),
            'templates': cycle_element.get('templates', ''),
            'skeletons': cycle_element.get('skeletons', ''),
            'frameworks': cycle_element.get('frameworks', ''),
            'libraries': cycle_element.get('libraries', ''),
            'modules': cycle_element.get('modules', ''),
            'packages': cycle_element.get('packages', ''),
            'components': cycle_element.get('components', ''),
            'plugins': cycle_element.get('plugins', ''),
            'extensions': cycle_element.get('extensions', ''),
            'addons': cycle_element.get('addons', ''),
            'integrations': cycle_element.get('integrations', ''),
            'connections': cycle_element.get('connections', ''),
            'interfaces': cycle_element.get('interfaces', ''),
            'adapters': cycle_element.get('adapters', ''),
            'drivers': cycle_element.get('drivers', ''),
            'protocols': cycle_element.get('protocols', ''),
            'standards': cycle_element.get('standards', ''),
            'formats': cycle_element.get('formats', ''),
            'schemas': cycle_element.get('schemas', ''),
            'specifications': cycle_element.get('specifications', ''),
            'contracts': cycle_element.get('contracts', ''),
            'agreements': cycle_element.get('agreements', ''),
            'licenses': cycle_element.get('licenses', ''),
            'copyright': cycle_element.get('copyright', ''),
            'trademark': cycle_element.get('trademark', ''),
            'patent': cycle_element.get('patent', ''),
            'intellectual_property': cycle_element.get('intellectual_property', ''),
            'proprietary': cycle_element.get('proprietary', ''),
            'open_source': cycle_element.get('open_source', ''),
            'public_domain': cycle_element.get('public_domain', ''),
            'free_software': cycle_element.get('free_software', ''),
            'oss': cycle_element.get('oss', ''),
            'foss': cycle_element.get('foss', ''),
            'gpl': cycle_element.get('gpl', ''),
            'mit': cycle_element.get('mit', ''),
            'apache': cycle_element.get('apache', ''),
            'bsd': cycle_element.get('bsd', ''),
            'cc': cycle_element.get('cc', ''),
            'unlicense': cycle_element.get('unlicense', ''),
            'wtfpl': cycle_element.get('wtfpl', ''),
            'agpl': cycle_element.get('agpl', ''),
            'lgpl': cycle_element.get('lgpl', ''),
            'epl': cycle_element.get('epl', ''),
            'mpl': cycle_element.get('mpl', ''),
            'osl': cycle_element.get('osl', ''),
            'afl': cycle_element.get('afl', ''),
            'cddl': cycle_element.get('cddl', ''),
            'ecl': cycle_element.get('ecl', ''),
            'eupl': cycle_element.get('eupl', ''),
            'frameworx': cycle_element.get('frameworx', ''),
            'gpl-compatible': cycle_element.get('gpl-compatible', ''),
            'gpl-incompatible': cycle_element.get('gpl-incompatible', ''),
            'lgpl-compatible': cycle_element.get('lgpl-compatible', ''),
            'lgpl-incompatible': cycle_element.get('lgpl-incompatible', ''),
            'other': cycle_element.get('other', '')
        }
        
        # Extract all attributes
        for attr_name, attr_value in cycle_element.attrib.items():
            if attr_name not in cycle:
                cycle[attr_name] = attr_value
        
        # Extract text content which might contain cycle values
        if cycle_element.text:
            # This is a simplified approach - real implementation might vary
            # based on how cycles are defined in the XML
            cycle_text = cycle_element.text.strip()
            if cycle_text:
                cycle['values'] = [cycle_text]
        
        # Look for nested elements that might contain cycle information
        for child in cycle_element:
            if child.tag.lower() in ['value', 'val', 'entry']:
                cycle['values'].append(child.text or '')
            elif child.tag.lower() in ['dependency', 'depends', 'prereq']:
                cycle['dependencies'].append({
                    'type': child.tag,
                    'condition': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'condition':
                cycle['conditions'].append({
                    'type': child.get('type', ''),
                    'expression': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'action':
                cycle['actions'].append({
                    'type': child.get('type', ''),
                    'target': child.get('target', ''),
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'trigger':
                cycle['triggers'].append({
                    'type': child.get('type', ''),
                    'condition': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'notification':
                cycle['notifications'].append({
                    'type': child.get('type', ''),
                    'target': child.get('target', ''),
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'logging':
                cycle['logging'].append({
                    'level': child.get('level', ''),
                    'target': child.get('target', ''),
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'monitoring':
                cycle['monitoring'].append({
                    'type': child.get('type', ''),
                    'target': child.get('target', ''),
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'metric':
                cycle['metrics'].append({
                    'name': child.get('name', ''),
                    'value': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'performance':
                cycle['performance'].append({
                    'metric': child.get('metric', ''),
                    'value': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'efficiency':
                cycle['efficiency'].append({
                    'metric': child.get('metric', ''),
                    'value': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'cost':
                cycle['cost'].append({
                    'type': child.get('type', ''),
                    'amount': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'budget':
                cycle['budget'].append({
                    'type': child.get('type', ''),
                    'amount': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'charge':
                cycle['charge'].append({
                    'type': child.get('type', ''),
                    'amount': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'rate':
                cycle['rate'].append({
                    'type': child.get('type', ''),
                    'value': child.text or '',
                    'attributes': dict(child.attrib)
                })
            elif child.tag.lower() == 'price':
                cycle['price'].append({
                    'type': child.get('type', ''),
                    'value': child.text or '',
                    'attributes': dict(child.attrib)
                })
        
        return cycle
    
    def _parse_legacy_cycles(self, cycles_element: ET.Element) -> List[Dict[str, Any]]:
        """
        Parse cycle definitions from legacy workflow XML format.
        
        Args:
            cycles_element: XML element containing cycles
            
        Returns:
            List of parsed cycle dictionaries
        """
        cycles = []
        
        for child in cycles_element:
            if child.tag.lower() in ['cycledef', 'cycle', 'cycledefs']:
                cycle = self._parse_cycle(child)
                # Apply legacy-specific transformations
                cycles.append(cycle)
        
        return cycles
    
    def _parse_resources(self, resources_element: ET.Element) -> List[Dict[str, Any]]:
        """
        Parse resources from the workflow XML.
        
        Args:
            resources_element: XML element containing resources
            
        Returns:
            List of parsed resource dictionaries
        """
        resources = []
        
        for child in resources_element:
            resource = {
                'type': child.tag,
                'attributes': dict(child.attrib),
                'settings': {},
                'name': child.get('name', ''),
                'id': child.get('id', ''),
                'value': child.text or '',
                'unit': child.get('unit', ''),
                'min': child.get('min', ''),
                'max': child.get('max', ''),
                'default': child.get('default', ''),
                'required': child.get('required', 'false').lower() == 'true',
                'optional': child.get('optional', 'true').lower() == 'true',
                'enabled': child.get('enabled', 'true').lower() == 'true',
                'active': child.get('active', 'true').lower() == 'true',
                'status': child.get('status', 'active'),
                'dependencies': [],
                'conditions': [],
                'actions': [],
                'triggers': [],
                'notifications': [],
                'logging': [],
                'monitoring': [],
                'metrics': [],
                'performance': [],
                'efficiency': [],
                'cost': [],
                'budget': [],
                'charge': [],
                'rate': [],
                'price': [],
                'currency': child.get('currency', ''),
                'payment': child.get('payment', ''),
                'billing': child.get('billing', ''),
                'accounting': child.get('accounting', ''),
                'security': child.get('security', ''),
                'encryption': child.get('encryption', ''),
                'authentication': child.get('authentication', ''),
                'authorization': child.get('authorization', ''),
                'certification': child.get('certification', ''),
                'validation': child.get('validation', ''),
                'verification': child.get('verification', ''),
                'compliance': child.get('compliance', ''),
                'regulatory': child.get('regulatory', ''),
                'policy': child.get('policy', ''),
                'governance': child.get('governance', ''),
                'management': child.get('management', ''),
                'administration': child.get('administration', ''),
                'operations': child.get('operations', ''),
                'maintenance': child.get('maintenance', ''),
                'support': child.get('support', ''),
                'help': child.get('help', ''),
                'documentation': child.get('documentation', ''),
                'tutorial': child.get('tutorial', ''),
                'examples': child.get('examples', ''),
                'samples': child.get('samples', ''),
                'templates': child.get('templates', ''),
                'skeletons': child.get('skeletons', ''),
                'frameworks': child.get('frameworks', ''),
                'libraries': child.get('libraries', ''),
                'modules': child.get('modules', ''),
                'packages': child.get('packages', ''),
                'components': child.get('components', ''),
                'plugins': child.get('plugins', ''),
                'extensions': child.get('extensions', ''),
                'addons': child.get('addons', ''),
                'integrations': child.get('integrations', ''),
                'connections': child.get('connections', ''),
                'interfaces': child.get('interfaces', ''),
                'adapters': child.get('adapters', ''),
                'drivers': child.get('drivers', ''),
                'protocols': child.get('protocols', ''),
                'standards': child.get('standards', ''),
                'formats': child.get('formats', ''),
                'schemas': child.get('schemas', ''),
                'specifications': child.get('specifications', ''),
                'contracts': child.get('contracts', ''),
                'agreements': child.get('agreements', ''),
                'licenses': child.get('licenses', ''),
                'copyright': child.get('copyright', ''),
                'trademark': child.get('trademark', ''),
                'patent': child.get('patent', ''),
                'intellectual_property': child.get('intellectual_property', ''),
                'proprietary': child.get('proprietary', ''),
                'open_source': child.get('open_source', ''),
                'public_domain': child.get('public_domain', ''),
                'free_software': child.get('free_software', ''),
                'oss': child.get('oss', ''),
                'foss': child.get('foss', ''),
                'gpl': child.get('gpl', ''),
                'mit': child.get('mit', ''),
                'apache': child.get('apache', ''),
                'bsd': child.get('bsd', ''),
                'cc': child.get('cc', ''),
                'unlicense': child.get('unlicense', ''),
                'wtfpl': child.get('wtfpl', ''),
                'agpl': child.get('agpl', ''),
                'lgpl': child.get('lgpl', ''),
                'epl': child.get('epl', ''),
                'mpl': child.get('mpl', ''),
                'osl': child.get('osl', ''),
                'afl': child.get('afl', ''),
                'cddl': child.get('cddl', ''),
                'ecl': child.get('ecl', ''),
                'eupl': child.get('eupl', ''),
                'frameworx': child.get('frameworx', ''),
                'gpl-compatible': child.get('gpl-compatible', ''),
                'gpl-incompatible': child.get('gpl-incompatible', ''),
                'lgpl-compatible': child.get('lgpl-compatible', ''),
                'lgpl-incompatible': child.get('lgpl-incompatible', ''),
                'other': child.get('other', '')
            }
            
            # Extract resource-specific attributes
            for attr_name, attr_value in child.attrib.items():
                if attr_name not in resource:
                    resource['settings'][attr_name] = attr_value
            
            # Extract nested elements
            for nested_child in child:
                if nested_child.tag.lower() in ['dependency', 'depends', 'prereq']:
                    resource['dependencies'].append({
                        'type': nested_child.tag,
                        'condition': nested_child.text or '',
                        'attributes': dict(nested_child.attrib)
                    })
                elif nested_child.tag.lower() == 'condition':
                    resource['conditions'].append({
                        'type': nested_child.get('type', ''),
                        'expression': nested_child.text or '',
                        'attributes': dict(nested_child.attrib)
                    })
                elif nested_child.tag.lower() == 'action':
                    resource['actions'].append({
                        'type': nested_child.get('type', ''),
                        'target': nested_child.get('target', ''),
                        'attributes': dict(nested_child.attrib)
                    })
                elif nested_child.tag.lower() == 'trigger':
                    resource['triggers'].append({
                        'type': nested_child.get('type', ''),
                        'condition': nested_child.text or '',
                        'attributes': dict(nested_child.attrib)
                    })
                elif nested_child.tag.lower() == 'notification':
                    resource['notifications'].append({
                        'type': nested_child.get('type', ''),
                        'target': nested_child.get('target', ''),
                        'attributes': dict(nested_child.attrib)
                    })
                elif nested_child.tag.lower() == 'logging':
                    resource['logging'].append({
                        'level': nested_child.get('level', ''),
                        'target': nested_child.get('target', ''),
                        'attributes': dict(nested_child.attrib)
                    })
                elif nested_child.tag.lower() == 'monitoring':
                    resource['monitoring'].append({
                        'type': nested_child.get('type', ''),
                        'target': nested_child.get('target', ''),
                        'attributes': dict(nested_child.attrib)
                    })
                elif nested_child.tag.lower() == 'metric':
                    resource['metrics'].append({
                        'name': nested_child.get('name', ''),
                        'value': nested_child.text or '',
                        'attributes': dict(nested_child.attrib)
                    })
                elif nested_child.tag.lower() == 'performance':
                    resource['performance'].append({
                        'metric': nested_child.get('metric', ''),
                        'value': nested_child.text or '',
                        'attributes': dict(nested_child.attrib)
                    })
                elif nested_child.tag.lower() == 'efficiency':
                    resource['efficiency'].append({
                        'metric': nested_child.get('metric', ''),
                        'value': nested_child.text or '',
                        'attributes': dict(nested_child.attrib)
                    })
                elif nested_child.tag.lower() == 'cost':
                    resource['cost'].append({
                        'type': nested_child.get('type', ''),
                        'amount': nested_child.text or '',
                        'attributes': dict(nested_child.attrib)
                    })
                elif nested_child.tag.lower() == 'budget':
                    resource['budget'].append({
                        'type': nested_child.get('type', ''),
                        'amount': nested_child.text or '',
                        'attributes': dict(nested_child.attrib)
                    })
                elif nested_child.tag.lower() == 'charge':
                    resource['charge'].append({
                        'type': nested_child.get('type', ''),
                        'amount': nested_child.text or '',
                        'attributes': dict(nested_child.attrib)
                    })
                elif nested_child.tag.lower() == 'rate':
                    resource['rate'].append({
                        'type': nested_child.get('type', ''),
                        'value': nested_child.text or '',
                        'attributes': dict(nested_child.attrib)
                    })
                elif nested_child.tag.lower() == 'price':
                    resource['price'].append({
                        'type': nested_child.get('type', ''),
                        'value': nested_child.text or '',
                        'attributes': dict(nested_child.attrib)
                    })
            
            resources.append(resource)
        
        return resources
    
    def _parse_legacy_resources(self, resources_element: ET.Element) -> List[Dict[str, Any]]:
        """
        Parse resources from legacy workflow XML format.
        
        Args:
            resources_element: XML element containing resources
            
        Returns:
            List of parsed resource dictionaries
        """
        resources = []
        
        for child in resources_element:
            # Apply legacy-specific parsing
            resource = self._parse_resources(child)[0] if self._parse_resources(child) else {}
            if resource:
                resources.append(resource)
        
        return resources
    
    def _get_current_timestamp(self) -> str:
        """
        Get the current timestamp in ISO format.
        
        Returns:
            Current timestamp as ISO string
        """
        return datetime.now().isoformat()
    
    def _get_task_color(self, status: str) -> str:
        """
        Get a color based on task status for visualization.
        
        Args:
            status: Task status
            
        Returns:
            Color string for the status
        """
        status_lower = status.lower()
        if status_lower in ['success', 'succeeded', 'completed', 's']:
            return 'green'
        elif status_lower in ['failed', 'error', 'f']:
            return 'red'
        elif status_lower in ['running', 'active', 'r']:
            return 'blue'
        elif status_lower in ['queued', 'pending', 'q']:
            return 'yellow'
        elif status_lower in ['held', 'h']:
            return 'orange'
        else:
            return 'gray'
    
    def _get_task_size(self, status: str) -> str:
        """
        Get a size based on task status for visualization.
        
        Args:
            status: Task status
            
        Returns:
            Size string for the status
        """
        status_lower = status.lower()
        if status_lower in ['success', 'succeeded', 'completed', 's']:
            return 'large'
        elif status_lower in ['failed', 'error', 'f']:
            return 'large'
        elif status_lower in ['running', 'active', 'r']:
            return 'medium'
        elif status_lower in ['queued', 'pending', 'q']:
            return 'small'
        elif status_lower in ['held', 'h']:
            return 'medium'
        else:
            return 'small'
    
    def validate_workflow(self, workflow_data: Dict[str, Any]) -> bool:
        """
        Validate parsed workflow data.
        
        Args:
            workflow_data: Parsed workflow data to validate
            
        Returns:
            True if workflow data is valid, False otherwise
        """
        if not workflow_data:
            return False
        
        # Check for required fields
        required_fields = ['id', 'tasks', 'source']
        for field in required_fields:
            if field not in workflow_data:
                self.logger.warning(f"Missing required field in workflow data: {field}")
                return False
        
        return True
    
    def parse_task_status(self, raw_status: str) -> str:
        """
        Parse and normalize a task status.
        
        Args:
            raw_status: Raw status string from workflow
            
        Returns:
            Normalized status string
        """
        normalized = self.visualization_config['status_mapping'].get(raw_status.upper(), raw_status.upper())
        return normalized
    
    def update_task_status(self, workflow_id: str, task_id: str, new_status: str) -> bool:
        """
        Update the status of a specific task in the workflow.
        
        Args:
            workflow_id: ID of the workflow
            task_id: ID of the task
            new_status: New status for the task
            
        Returns:
            True if update was successful
        """
        # This would update the workflow data in memory
        # For now, this is a placeholder implementation
        self.logger.info(f"Updated task {task_id} in workflow {workflow_id} to status {new_status}")
        return True