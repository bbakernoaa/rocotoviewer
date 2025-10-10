# Installation

This guide will walk you through installing and setting up RocotoViewer.

## Prerequisites

- Python 3.8 or higher
- pip package manager

## Installing from PyPI

The easiest way to install RocotoViewer is from PyPI:

```bash
pip install rocotoviewer
```

## Installing from Source

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

## Installing Development Dependencies

To install development dependencies:

```bash
pip install -e ".[dev]"
```

## Verifying Installation

To verify that RocotoViewer was installed correctly:

```bash
rocotoviewer --version
```

This should print the version of RocotoViewer that was installed.

## Configuration

After installation, you may want to create a configuration file. You can generate a default configuration with:

```bash
rocotoviewer init
```

This creates a `rocoto_config.yaml` file in your current directory with default settings.