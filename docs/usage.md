# Usage

This guide explains how to use RocotoViewer to monitor and manage your Rocoto workflows.

## Command Line Interface

RocotoViewer provides a comprehensive command-line interface for managing workflows.

### Basic Usage

To start the interactive viewer:

```bash
rocotoviewer
```

To view a specific workflow:

```bash
rocotoviewer view --workflow /path/to/workflow.xml
```

To monitor a directory for workflow changes:

```bash
rocotoviewer monitor --directory /path/to/workflows/
```

### Configuration

You can specify a configuration file:

```bash
rocotoviewer --config /path/to/config.yaml
```

### Available Commands

- `view`: View a workflow in the UI
- `monitor`: Monitor a directory for workflow changes
- `parse`: Parse a workflow file and display information
- `init`: Initialize a new configuration file

## Configuration File

RocotoViewer uses a YAML configuration file. Here's an example:

```yaml
workflows:
  - path: "/path/to/workflow.xml"
    name: "Production Workflow"
    monitor: true

display:
  theme: "default"
  refresh_interval: 5
  max_log_lines: 1000

monitor:
  enabled: true
  poll_interval: 10
  max_file_size: 10485760  # 10MB

logging:
  level: "INFO"
  file: "/path/to/logfile.log"
```

## Using the UI

When you launch RocotoViewer without arguments, it opens an interactive terminal UI:

- Use arrow keys to navigate
- Press `M` to return to the main view
- Press `L` to view logs
- Press `Q` or `Ctrl+C` to quit
- Press `R` to refresh the view

## API Usage

You can also use RocotoViewer as a library in your Python code:

```python
from rocotoviewer.ui.app import RocotoViewerApp
from rocotoviewer.config.config import Config

# Create configuration
config = Config.load("/path/to/config.yaml")

# Initialize components
from rocotoviewer.core.state_manager import StateManager
from rocotoviewer.core.log_processor import LogProcessor
from rocotoviewer.parsers.workflow_parser import WorkflowParser

state_manager = StateManager(config)
log_processor = LogProcessor(config)
workflow_parser = WorkflowParser(config)

# Create and run the application
app = RocotoViewerApp(config, state_manager, log_processor, workflow_parser)
app.run()