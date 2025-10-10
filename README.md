# RocotoViewer

A powerful viewer for Rocoto workflow management systems, providing real-time monitoring and visualization of workflow states.

## Features

- Real-time workflow state visualization
- Interactive log viewing and filtering
- Workflow dependency graph display
- Task status monitoring
- Configuration management
- Command-line interface for automation

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installing from PyPI (Recommended)

The easiest way to install RocotoViewer is from PyPI:

```bash
pip install rocotoviewer
```

### Installing from Source

To install from source:

1. Clone the repository:
   ```bash
   git clone https://github.com/rocotoviewer/rocotoviewer.git
   cd rocotoviewer
   ```

2. Install the package in development mode:
   ```bash
   pip install -e .
   ```

Or install the package normally:
```bash
pip install .
```

### Installing Development Dependencies

To install development dependencies:
```bash
pip install -e ".[dev]"
```

## Usage

### Command Line Interface

```bash
# Basic usage
rocotoviewer --config /path/to/config.yaml

# View workflow
rocotoviewer view --workflow /path/to/workflow.xml

# Monitor workflow directory
rocotoviewer monitor --directory /path/to/workflows/
```

### As a library

```python
from rocotoviewer.ui.app import RocotoViewerApp

app = RocotoViewerApp()
app.run()
```

## Configuration

Create a configuration file to specify workflow locations, display preferences, and other settings:

```yaml
workflows:
  - path: "/path/to/workflow.xml"
    name: "Production Workflow"
    monitor: true

display:
  theme: "default"
  refresh_interval: 5
  max_log_lines: 1000

logging:
  level: "INFO"
  file: "/path/to/logfile.log"
```

## Development

### Setup

```bash
git clone https://github.com/rocotoviewer/rocotoviewer.git
cd rocotoviewer
pip install -e ".[dev]"
```

### Run tests

```bash
pytest
```

### Build documentation

```bash
pip install -e ".[docs]"
mkdocs serve
```

## Verifying Installation

To verify that RocotoViewer was installed correctly:

```bash
rocotoviewer --version
```

This should print the version of RocotoViewer that was installed.

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for more details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.