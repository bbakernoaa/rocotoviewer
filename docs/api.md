# API Reference

This document provides a reference for the RocotoViewer API.

## Core Modules

### Config Module

#### `Config`
Main configuration class for RocotoViewer.

- `load(config_path: Optional[Path]) -> Config`: Load configuration from a YAML file
- `from_dict(data: Dict[str, Any]) -> Config`: Create Config instance from dictionary
- `to_dict() -> Dict[str, Any]`: Convert Config instance to dictionary
- `save(config_path: Path)`: Save configuration to a YAML file

#### `WorkflowConfig`
Configuration for a single workflow.

- `path: str`: Path to the workflow file
- `name: str`: Name of the workflow
- `monitor: bool`: Whether to monitor this workflow

#### `DisplayConfig`
Configuration for display settings.

- `theme: str`: Theme name
- `refresh_interval: int`: Refresh interval in seconds
- `max_log_lines: int`: Maximum number of log lines to display

### Core Module

#### `LogProcessor`
Handles processing of workflow logs.

- `__init__(config)`: Initialize with configuration
- `read_log_file(log_path: Path, max_lines: Optional[int] = None) -> List[str]`: Read log file with optional line limit
- `parse_log_line(line: str) -> Dict[str, Any]`: Parse a single log line into structured data
- `filter_logs(logs: List[Dict[str, Any]], level: Optional[str] = None, task_id: Optional[str] = None, status: Optional[str] = None, search_term: Optional[str] = None) -> List[Dict[str, Any]]`: Filter logs based on various criteria

#### `FileMonitor`
Monitors workflow files and directories for changes.

- `__init__(config, state_manager)`: Initialize with configuration and state manager
- `start()`: Start monitoring files
- `stop()`: Stop monitoring files
- `add_path(path: Path)`: Add a path to monitor

#### `StateManager`
Manages application state including workflow data, UI state, and user preferences.

- `__init__(config)`: Initialize with configuration
- `get(key: str, default: Any = None) -> Any`: Get a value from the state
- `set(key: str, value: Any)`: Set a value in the state
- `update_workflow(workflow_id: str, workflow_data: Dict[str, Any])`: Update workflow data in the state
- `get_workflow(workflow_id: str) -> Optional[Dict[str, Any]]`: Get workflow data from the state

#### `EventBus`
Centralized event bus for application communication.

- `subscribe(event_type: str, handler: Callable)`: Subscribe to an event type
- `publish(event: Union[Event, str], data: Any = None, source: str = None)`: Publish an event to all subscribed handlers
- `unsubscribe(event_type: str, handler: Callable)`: Unsubscribe from an event type

### Parsers Module

#### `WorkflowParser`
Parser for Rocoto workflow XML files.

- `__init__(config=None)`: Initialize the workflow parser
- `parse(source: str) -> Dict[str, Any]`: Parse a Rocoto workflow XML file
- `validate_workflow(workflow_data: Dict[str, Any]) -> bool`: Validate parsed workflow data

#### `LogParser`
Parser for workflow log files.

- `__init__(config=None)`: Initialize the log parser
- `parse(source: str) -> Dict[str, Any]`: Parse a log file and extract structured information
- `filter_logs(log_data: Dict[str, Any], level: str = None, task_id: str = None, status: str = None, search_term: str = None) -> Dict[str, Any]`: Filter parsed logs based on criteria

#### `TaskParser`
Parser for individual task definitions within workflow files.

- `__init__(config=None)`: Initialize the task parser
- `parse(source: str) -> Dict[str, Any]`: Parse task definitions from a source
- `get_task_summary(task_data: Dict[str, Any]) -> Dict[str, Any]`: Get a summary of parsed task data

### UI Module

#### `RocotoViewerApp`
Main UI application for RocotoViewer.

- `__init__(config, state_manager, log_processor, workflow_parser)`: Initialize the application
- `run()`: Run the application
- `refresh()`: Refresh the application display
- `load_workflow(workflow_path: str)`: Load a workflow into the application

## Utilities

### `FileUtils`
Utility class for file operations.

- `find_files(directory: Path, extensions: Optional[Union[str, List[str]]] = None, recursive: bool = True) -> List[Path]`: Find files in a directory with specific extensions
- `get_file_size(file_path: Path) -> int`: Get the size of a file in bytes
- `safe_read_file(file_path: Path, encoding: str = 'utf-8', max_size: int = 10 * 1024 * 1024) -> Optional[str]`: Safely read a file with size limits and error handling

### `TimeUtils`
Utility class for time operations.

- `format_timestamp(timestamp: Union[datetime, float], format_str: str = "%Y-%m-%d %H:%M:%S") -> str`: Format a timestamp into a readable string
- `parse_timestamp(timestamp_str: str, format_str: Optional[str] = None) -> Optional[datetime]`: Parse a timestamp string into a datetime object
- `format_duration(seconds: float) -> str`: Format a duration in seconds into a human-readable string

### `FormattingUtils`
Utility class for formatting operations.

- `format_workflow_status(status: str) -> str`: Format workflow status for display
- `format_task_summary(tasks: List[Dict[str, Any]]) -> Dict[str, int]`: Create a summary of task statuses
- `format_json(data: Any, indent: int = 2) -> str`: Format data as indented JSON string
- `format_percentage(value: float, total: float, decimals: int = 2) -> str`: Format a value as a percentage of a total