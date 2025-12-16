"""
Workflow parser module for RocotoViewer.

This module parses Rocoto workflow XML files and extracts structured data
using the standard library's ElementTree for performance and dataclasses for a clean data model.
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET
from datetime import datetime

from core.models import Task, Workflow, Dependency, Envar, Cycle, Resource
from .base_parser import BaseParser


class WorkflowParser(BaseParser):
    """
    A performant parser for Rocoto workflow XML files using ElementTree and dataclasses,
    with support for legacy formats and visualization data.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the workflow parser.
        """
        super().__init__(config)
        self.logger = logging.getLogger(self.__class__.__name__)

    def parse(self, source: str) -> Optional[Workflow]:
        """
        Parse a Rocoto workflow XML file into a Workflow object.
        """
        if not self.validate_source(source):
            self.logger.warning(f"Invalid or non-existent source file: {source}")
            return None

        try:
            tree = ET.parse(source)
            root = tree.getroot()

            workflow = self._parse_workflow_xml(root, source)

            if self._is_legacy(root):
                workflow = self._parse_legacy_workflow_xml(root, source)

            self._enhance_with_visualization_data(workflow)

            return workflow

        except ET.ParseError as e:
            self.logger.error(f"XML parsing error in {source}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error parsing workflow {source}: {e}")
            return None

    def _is_legacy(self, root: ET.Element) -> bool:
        """
        Detect if the workflow XML is in a legacy format.
        """
        return root.find('taskdef') is not None

    def _parse_workflow_xml(self, root: ET.Element, source: str) -> Workflow:
        """
        Parse the workflow XML and extract structured data in a single pass.
        """
        workflow_id = root.get('workflowid', Path(source).stem)
        workflow_name = root.get('name', workflow_id)
        description_element = root.find('description')
        description = description_element.text.strip() if description_element is not None and description_element.text else ""

        tasks = []
        cycles = []
        resources = []

        for element in root:
            if element.tag == 'task':
                tasks.append(self._create_task_from_element(element))
            elif element.tag == 'tasks':
                for task_element in element:
                    tasks.append(self._create_task_from_element(task_element))
            elif element.tag == 'cycledef':
                cycles.append(self._create_cycle_from_element(element))
            elif element.tag == 'resources':
                for pool in element.findall('pool/entry'):
                    resources.append(self._create_resource_from_element(pool))

        return Workflow(
            id=workflow_id,
            name=workflow_name,
            description=description,
            source_file=source,
            tasks=tasks,
            cycles=cycles,
            resources=resources,
        )

    def _parse_legacy_workflow_xml(self, root: ET.Element, source: str) -> Workflow:
        """
        Parse legacy workflow XML format.
        """
        workflow = self._parse_workflow_xml(root, source)
        # Add any legacy-specific parsing logic here
        return workflow

    def _create_task_from_element(self, task_element: ET.Element) -> Task:
        """
        Create a Task object from an XML element, capturing all nested tag data.
        """
        task_id = task_element.get('name', task_element.get('id', ''))
        command = ""
        dependencies = []
        envars = []
        attributes = dict(task_element.attrib)

        for child in task_element:
            tag = child.tag.lower()
            if tag == 'command':
                command = child.text.strip() if child.text else ""
            elif tag == 'dependency':
                dependencies.append(self._create_dependency_from_element(child))
            elif tag == 'envar':
                envars.append(self._create_envar_from_element(child))
            elif child.text and child.text.strip():
                 attributes[child.tag] = child.text.strip()

        return Task(
            id=task_id,
            command=command,
            dependencies=dependencies,
            envars=envars,
            attributes=attributes,
        )

    def _create_dependency_from_element(self, dep_element: ET.Element) -> Dependency:
        """
        Create a Dependency object from an XML element.
        """
        return Dependency(
            type=dep_element.tag,
            attributes=dict(dep_element.attrib),
            text=dep_element.text.strip() if dep_element.text else ""
        )

    def _create_envar_from_element(self, envar_element: ET.Element) -> Envar:
        """
        Create an Envar object from an XML element.
        """
        return Envar(
            name=envar_element.get('name', ''),
            value=envar_element.get('value', envar_element.text or ''),
        )

    def _create_cycle_from_element(self, cycle_element: ET.Element) -> Cycle:
        """
        Create a Cycle object from a cycledef XML element.
        """
        return Cycle(
            group=cycle_element.get('group'),
            text=cycle_element.text.strip() if cycle_element.text else ""
        )

    def _create_resource_from_element(self, resource_element: ET.Element) -> Resource:
        """
        Create a Resource object from a resource pool entry XML element.
        """
        return Resource(
            key=resource_element.get('key'),
            value=resource_element.get('value')
        )

    def _enhance_with_visualization_data(self, workflow: Workflow) -> None:
        """
        Enhance workflow data with visualization-specific information.
        """
        workflow.dependencies = self._calculate_dependencies(workflow.tasks)
        workflow.timeline = self._calculate_timeline(workflow.tasks)
        workflow.task_groups = self._calculate_task_groups(workflow.tasks)
        workflow.statistics = self._calculate_statistics(workflow)
        for i, task in enumerate(workflow.tasks):
            task.visualization['position'] = {'x': (i % 5) * 10, 'y': (i // 5) * 50}

    def _calculate_dependencies(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        """
        Calculate task dependencies from the task data.
        """
        # This is a simplified version of the original logic
        dependencies = []
        for task in tasks:
            for dep in task.dependencies:
                dependencies.append({
                    'source': task.id,
                    'target': dep.attributes.get('task', 'unknown'),
                })
        return dependencies

    def _calculate_timeline(self, tasks: List[Task]) -> Dict[str, Any]:
        """
        Calculate timeline information for tasks.
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
            start_time = task.attributes.get('start_time')
            end_time = task.attributes.get('end_time')
            
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

    def _calculate_task_groups(self, tasks: List[Task]) -> List[Dict[str, Any]]:
        """
        Group tasks based on common attributes.
        """
        groups = {}
        for task in tasks:
            status = task.attributes.get('status', 'unknown')
            if status not in groups:
                groups[status] = []
            groups[status].append(task.id)
        
        return [{'name': name, 'tasks': tasks} for name, tasks in groups.items()]

    def _calculate_statistics(self, workflow: Workflow) -> Dict[str, Any]:
        """
        Calculate statistics for the workflow.
        """
        return {
            'total_tasks': len(workflow.tasks),
            'dependency_count': len(workflow.dependencies),
            'task_groups_count': len(workflow.task_groups),
        }
