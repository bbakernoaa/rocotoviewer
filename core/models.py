"""
Core data models for RocotoViewer.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Dependency:
    """
    Represents a task dependency.
    """
    type: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    text: str = ""


@dataclass
class Envar:
    """
    Represents an environment variable for a task.
    """
    name: str
    value: str


@dataclass
class Cycle:
    """
    Represents a cycle definition in a workflow.
    """
    group: Optional[str]
    text: str


@dataclass
class Resource:
    """
    Represents a resource in a workflow's resource pool.
    """
    key: Optional[str]
    value: Optional[str]


@dataclass
class Task:
    """
    Represents a task in a Rocoto workflow.
    """
    id: str
    command: str = ""
    dependencies: List[Dependency] = field(default_factory=list)
    envars: List[Envar] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    visualization: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Workflow:
    """
    Represents a Rocoto workflow.
    """
    id: str
    name: str
    description: str = ""
    tasks: List[Task] = field(default_factory=list)
    source_file: str = ""
    cycles: List[Cycle] = field(default_factory=list)
    resources: List[Resource] = field(default_factory=list)
    dependencies: List[Dict[str, Any]] = field(default_factory=list)
    timeline: Dict[str, Any] = field(default_factory=dict)
    task_groups: List[Dict[str, Any]] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    visualization: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
