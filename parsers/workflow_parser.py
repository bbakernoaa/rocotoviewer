"""
Workflow parser module for RocotoViewer.

This module parses Rocoto workflow XML files and extracts structured data
using the standard library's ElementTree for performance and dataclasses for a clean data model.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET
from collections import defaultdict
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
        Parse a Rocoto workflow XML file into a Workflow object in a single pass.
        """
        if not self.validate_source(source):
            self.logger.warning(f"Invalid or non-existent source file: {source}")
            return None
        try:
            tree = ET.parse(source)
            root = tree.getroot()

            is_legacy = self._is_legacy(root)

            return self._parse_and_enhance_workflow(root, source, is_legacy)
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
        return root.find("taskdef") is not None

    def _parse_and_enhance_workflow(
        self, root: ET.Element, source: str, is_legacy: bool
    ) -> Workflow:
        """
        Parse the workflow XML and enhance it with visualization data in a single pass.
        """
        workflow_id = root.get("workflowid", Path(source).stem)
        workflow_name = root.get("name", workflow_id)
        description_element = root.find("description")
        description = (
            description_element.text.strip()
            if description_element is not None and description_element.text
            else ""
        )

        tasks, cycles, resources, start_times, end_times = [], [], [], [], []
        task_groups = defaultdict(list)

        task_elements = root.findall("task") + root.findall("tasks/task")
        if is_legacy:
            # Add logic to find tasks in legacy format, if different
            pass

        for i, task_element in enumerate(task_elements):
            task = self._create_task_from_element(task_element)
            task.visualization["position"] = {"x": (i % 5) * 10, "y": (i // 5) * 50}
            tasks.append(task)

            self._extract_and_append_time(task, "start_time", start_times)
            self._extract_and_append_time(task, "end_time", end_times)

            status = task.attributes.get("status", "unknown")
            task_groups[status].append(task.id)

        dependencies = [
            {"source": task.id, "target": dep.attributes.get("task", "unknown")}
            for task in tasks
            for dep in task.dependencies
        ]

        for cycle_element in root.findall("cycledef"):
            cycles.append(self._create_cycle_from_element(cycle_element))

        for resource_element in root.findall("resources/pool/entry"):
            resources.append(self._create_resource_from_element(resource_element))

        timeline = self._calculate_timeline(start_times, end_times)

        formatted_task_groups = [
            {"name": name, "tasks": tasks_list}
            for name, tasks_list in task_groups.items()
        ]

        workflow = Workflow(
            id=workflow_id,
            name=workflow_name,
            description=description,
            source_file=source,
            tasks=tasks,
            cycles=cycles,
            resources=resources,
            dependencies=dependencies,
            timeline=timeline,
            task_groups=formatted_task_groups,
        )
        workflow.statistics = self._calculate_statistics(workflow)
        return workflow

    def _extract_and_append_time(
        self, task: Task, time_attribute: str, time_list: list
    ) -> None:
        """Extracts, parses, and appends a time attribute from a task to a list."""
        time_str = task.attributes.get(time_attribute)
        if time_str:
            try:
                time_dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
                time_list.append(time_dt)
            except ValueError:
                self.logger.warning(f"Could not parse datetime string: {time_str}")

    def _create_task_from_element(self, task_element: ET.Element) -> Task:
        """
        Create a Task object from an XML element, capturing all nested tag data.
        """
        task_id = task_element.get("name", task_element.get("id", ""))
        command = ""
        dependencies = []
        envars = []
        attributes = dict(task_element.attrib)

        for child in task_element:
            tag = child.tag.lower()
            if tag == "command":
                command = child.text.strip() if child.text else ""
            elif tag == "dependency":
                dependencies.append(self._create_dependency_from_element(child))
            elif tag == "envar":
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
            text=dep_element.text.strip() if dep_element.text else "",
        )

    def _create_envar_from_element(self, envar_element: ET.Element) -> Envar:
        """
        Create an Envar object from an XML element.
        """
        return Envar(
            name=envar_element.get("name", ""),
            value=envar_element.get("value", envar_element.text or ""),
        )

    def _create_cycle_from_element(self, cycle_element: ET.Element) -> Cycle:
        """
        Create a Cycle object from a cycledef XML element.
        """
        return Cycle(
            group=cycle_element.get("group"),
            text=cycle_element.text.strip() if cycle_element.text else "",
        )

    def _create_resource_from_element(self, resource_element: ET.Element) -> Resource:
        """
        Create a Resource object from a resource pool entry XML element.
        """
        return Resource(
            key=resource_element.get("key"), value=resource_element.get("value")
        )

    def _calculate_timeline(
        self, start_times: List[datetime], end_times: List[datetime]
    ) -> Dict[str, Any]:
        """
        Calculate timeline information from pre-parsed datetime lists.
        """
        timeline = {"earliest_start": None, "latest_end": None, "total_duration": 0}

        if start_times:
            timeline["earliest_start"] = min(start_times).isoformat()

        if end_times:
            timeline["latest_end"] = max(end_times).isoformat()

        if timeline["earliest_start"] and timeline["latest_end"]:
            try:
                start_dt = datetime.fromisoformat(timeline["earliest_start"])
                end_dt = datetime.fromisoformat(timeline["latest_end"])
                timeline["total_duration"] = (end_dt - start_dt).total_seconds()
            except ValueError:
                self.logger.warning(
                    "Could not calculate total_duration due to ISO format error."
                )
                pass

        return timeline

    def _calculate_statistics(self, workflow: Workflow) -> Dict[str, Any]:
        """
        Calculate statistics for the workflow.
        """
        return {
            "total_tasks": len(workflow.tasks),
            "dependency_count": len(workflow.dependencies),
            "task_groups_count": len(workflow.task_groups),
        }
