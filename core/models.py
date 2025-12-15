"""
Core data models for RocotoViewer.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class Task:
    """
    Represents a task in a Rocoto workflow.
    """
    id: str
    command: str = ""
    dependencies: List[Dict[str, Any]] = field(default_factory=list)
    envars: List[Dict[str, str]] = field(default_factory=list)
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
    cycles: List[Dict[str, Any]] = field(default_factory=list)
    resources: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[Dict[str, Any]] = field(default_factory=list)
    timeline: Dict[str, Any] = field(default_factory=dict)
    task_groups: List[Dict[str, Any]] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    visualization: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
