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
from collections import defaultdict

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
        Parse a Rocoto workflow XML file into a Workflow object using a memory-efficient,
        single-pass approach with iterparse.

        Why iterparse?
        While ET.parse() can be faster for small files, this implementation prioritizes
        memory efficiency and scalability for large workflows. The single-pass approach
        also improves code clarity by consolidating data processing into one loop,
        avoiding a second pass over the task list to generate visualization data.
        """
        if not self.validate_source(source):
            self.logger.warning(f"Invalid or non-existent source file: {source}")
            return None

        try:
            workflow = self._parse_workflow_with_iterparse(source)
            if workflow:
                self._process_workflow_data(workflow)
            return workflow

        except ET.ParseError as e:
            self.logger.error(f"XML parsing error in {source}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error parsing workflow {source}: {e}")
            return None

    def _parse_workflow_with_iterparse(self, source: str) -> Workflow:
        """
        Parse the workflow XML using iterparse for a memory-efficient single pass.
        """
        tasks = []
        cycles = []
        resources = []

        context = ET.iterparse(source, events=('start', 'end'))
        _, root = next(context)  # Get the root element

        workflow_id = root.get('workflowid', Path(source).stem)
        workflow_name = root.get('name', workflow_id)
        description_element = root.find('description')
        description = description_element.text.strip() if description_element is not None and description_element.text else ""

        is_legacy = self._is_legacy(root)

        for event, element in context:
            if event == 'end':
                tag = element.tag
                if tag == 'task' or (is_legacy and tag == 'taskdef'):
                    task = self._create_task_from_element(element)
                    tasks.append(task)
                    root.clear() # Free memory
                elif tag == 'cycledef':
                    cycles.append(self._create_cycle_from_element(element))
                elif tag == 'pool' and element.find('entry') is not None:
                     for entry in element.findall('entry'):
                        resources.append(self._create_resource_from_element(entry))


        return Workflow(
            id=workflow_id,
            name=workflow_name,
            description=description,
            source_file=source,
            tasks=tasks,
            cycles=cycles,
            resources=resources,
            dependencies=[],
            task_groups=[],
            timeline={}
        )

    def _is_legacy(self, root: ET.Element) -> bool:
        """
        Detect if the workflow XML is in a legacy format.
        """
        return root.find('taskdef') is not None

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

    def _process_workflow_data(self, workflow: Workflow) -> None:
        """
        Process the parsed workflow data to calculate dependencies, timelines,
        and other derived data in a single, efficient pass.
        """
        task_groups_map = defaultdict(list)
        start_times: List[datetime] = []
        end_times: List[datetime] = []

        for i, task in enumerate(workflow.tasks):
            # 1. Group tasks by status
            status = task.attributes.get('status', 'unknown')
            task_groups_map[status].append(task.id)

            # 2. Set visualization position
            task.visualization['position'] = {'x': (i % 5) * 10, 'y': (i // 5) * 50}

            # 3. Collect timeline data
            start_time_str = task.attributes.get('start_time')
            if start_time_str:
                try:
                    start_dt = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                    start_times.append(start_dt)
                except ValueError:
                    self.logger.warning(f"Invalid start_time format for task {task.id}: {start_time_str}")

            end_time_str = task.attributes.get('end_time')
            if end_time_str:
                try:
                    end_dt = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                    end_times.append(end_dt)
                except ValueError:
                    self.logger.warning(f"Invalid end_time format for task {task.id}: {end_time_str}")

        workflow.dependencies = [
            {'source': task.id, 'target': dep.attributes.get('task', 'unknown')}
            for task in workflow.tasks
            for dep in task.dependencies
        ]

        workflow.task_groups = [{'name': name, 'tasks': ts} for name, ts in task_groups_map.items()]

        earliest_start = min(start_times) if start_times else None
        latest_end = max(end_times) if end_times else None

        total_duration = 0
        if earliest_start and latest_end:
            total_duration = (latest_end - earliest_start).total_seconds()

        workflow.timeline = {
            'earliest_start': earliest_start.isoformat() if earliest_start else None,
            'latest_end': latest_end.isoformat() if latest_end else None,
            'total_duration': total_duration,
        }

        workflow.statistics = {
            'total_tasks': len(workflow.tasks),
            'dependency_count': len(workflow.dependencies),
            'task_groups_count': len(workflow.task_groups),
        }
