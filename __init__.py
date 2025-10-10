"""
RocotoViewer - A powerful viewer for Rocoto workflow management systems.

This package provides tools for visualizing, monitoring, and managing 
Rocoto-based workflow systems with a rich UI and command-line interface.
"""

__version__ = "0.1.0"

# Import main modules for easy access
from . import config
from . import core
from . import ui
from . import parsers
from . import utils

# Import CLI module for entry point
from . import cli

# Define what gets imported with "from rocotoviewer import *"
__all__ = [
    "config",
    "core", 
    "ui",
    "parsers",
    "utils",
    "cli",
    "__version__"
]

# Define the CLI entry point function
def main():
    """Main entry point for the CLI."""
    from .cli import main as cli_main
    return cli_main()