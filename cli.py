"""
Command Line Interface for RocotoViewer.

This module provides a CLI for launching the viewer, monitoring workflows,
and performing various operations from the command line with comprehensive
argument parsing and mode support.
"""

import click
import sys
import json
import yaml
from pathlib import Path
from typing import Optional, List
import os

from .main import run_app, run_monitor, run_parse, run_stats, run_config_commands
from .__version__ import __version__
from .config.config import Config


@click.group(invoke_without_command=True, help="RocotoViewer - A powerful viewer for Rocoto workflow management systems.")
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Path to configuration file')
@click.option('--workflow', '-w', type=click.Path(exists=True, path_type=Path),
              help='Path to workflow file to view')
@click.option('--version', '-v', is_flag=True, help='Show version and exit')
@click.option('--verbose', '-V', count=True, help='Increase verbosity (use -VV for debug)')
@click.option('--theme', type=str, default=None, help='UI theme to use')
@click.option('--follow', is_flag=True, help='Auto-follow workflow changes')
@click.option('--filter', type=str, default=None, help='Filter tasks by status or name')
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path], workflow: Optional[Path],
        version: bool, verbose: int, theme: str, follow: bool, filter: str) -> None:
    """
    RocotoViewer - A powerful viewer for Rocoto workflow management systems.
    
    RocotoViewer provides comprehensive tools for monitoring, visualizing, and managing
    Rocoto-based workflow systems. It offers both interactive and non-interactive modes
    for different use cases.
    
    Usage Examples:
      rocotoviewer                                  # Launch interactive UI
      rocotoviewer view -w workflow.xml             # View specific workflow
      rocotoviewer monitor -d /path/to/workflows    # Monitor directory
      rocotoviewer parse workflow.xml               # Parse workflow file
      rocotoviewer stats workflow.xml               # Show statistics
      rocotoviewer config --list                    # List configuration
    """
    if version:
        click.echo(f"RocotoViewer v{__version__}")
        return
    
    # Set up verbosity
    if verbose == 1:
        os.environ['ROCOTOVIEWER_LOG_LEVEL'] = 'INFO'
    elif verbose >= 2:
        os.environ['ROCOTOVIEWER_LOG_LEVEL'] = 'DEBUG'
    
    # Store additional options in context
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config
    ctx.obj['workflow_path'] = workflow
    ctx.obj['theme'] = theme
    ctx.obj['follow'] = follow
    ctx.obj['filter'] = filter
    
    if ctx.invoked_subcommand is None:
        # Default command - run the main application in interactive mode
        exit_code = run_app(config_path=config, workflow_path=workflow, 
                           theme=theme, follow=follow, filter_str=filter)
        sys.exit(exit_code)


@cli.command(help="View a workflow in the RocotoViewer UI (default mode).")
@click.argument('workflow_arg', required=False, type=click.Path(exists=True, path_type=Path))
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Path to configuration file')
@click.option('--workflow', '-w', type=click.Path(exists=True, path_type=Path),
              help='Path to workflow file to view')
@click.option('--database', '-d', type=click.Path(exists=True, path_type=Path),
              help='Path to database file')
@click.option('--log-files', '-l', multiple=True, type=click.Path(exists=True, path_type=Path),
              help='Path to log files to monitor')
@click.option('--theme', type=str, default=None, help='UI theme to use')
@click.option('--follow', is_flag=True, help='Auto-follow workflow changes')
@click.option('--filter', type=str, default=None, help='Filter tasks by status or name')
@click.option('--verbose', '-V', count=True, help='Increase verbosity (use -VV for debug)')
@click.pass_context
def view(ctx, workflow_arg: Optional[Path], config: Optional[Path], workflow: Optional[Path], database: Optional[Path],
         log_files: List[Path], theme: str, follow: bool, filter: str, verbose: int) -> None:
    """
    View a workflow in the RocotoViewer UI (default mode).
    
    This command launches the interactive Textual UI for viewing and monitoring
    workflow states in real-time. You can specify a workflow file to load
    directly, or let the viewer use configuration settings.
    
    Examples:
      rocotoviewer view workflow.xml                       # View specific workflow (positional)
      rocotoviewer view -w workflow.xml                    # View specific workflow (option)
      rocotoviewer view -c config.yaml -w workflow.xml     # Use specific config
      rocotoviewer view --theme dark                       # Use dark theme
      rocotoviewer view --filter running                   # Filter running tasks
    """
    # Use context values if not provided as command options
    config = config or ctx.obj.get('config_path')
    
    # Prioritize positional argument, then option, then context
    workflow = workflow_arg or workflow or ctx.obj.get('workflow_path')
    
    theme = theme or ctx.obj.get('theme')
    follow = follow or ctx.obj.get('follow')
    filter = filter or ctx.obj.get('filter')
    
    if verbose == 1:
        os.environ['ROCOTOVIEWER_LOG_LEVEL'] = 'INFO'
    elif verbose >= 2:
        os.environ['ROCOTOVIEWER_LOG_LEVEL'] = 'DEBUG'
    
    exit_code = run_app(config_path=config, workflow_path=workflow, 
                       database_path=database, log_paths=list(log_files),
                       theme=theme, follow=follow, filter_str=filter)
    sys.exit(exit_code)


@cli.command(help="Monitor a directory or workflow for changes in real-time.")
@click.argument('path_arg', required=False, type=click.Path(exists=True, path_type=Path))
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Path to configuration file')
@click.option('--directory', '-d', type=click.Path(exists=True, path_type=Path),
              help='Directory to monitor for workflow files')
@click.option('--workflow', '-w', type=click.Path(exists=True, path_type=Path),
              help='Path to workflow file to monitor')
@click.option('--interval', '-i', type=int, default=10, help='Polling interval in seconds (default: 10)')
@click.option('--output', '-o', type=click.Path(path_type=Path),
              help='Output file for monitoring results')
@click.option('--format', type=click.Choice(['json', 'yaml', 'csv', 'text']),
              default='text', help='Output format (default: text)')
@click.option('--follow', is_flag=True, help='Continue monitoring indefinitely')
@click.option('--verbose', '-V', count=True, help='Increase verbosity (use -VV for debug)')
def monitor(path_arg: Optional[Path], config: Optional[Path], directory: Optional[Path], workflow: Optional[Path],
            interval: int, output: Optional[Path], format: str, follow: bool, verbose: int) -> None:
    """
    Monitor a directory or workflow for changes in real-time.
    
    This command monitors workflow files for changes and can output results
    in various formats. It's useful for tracking workflow progress without
    launching the interactive UI.
    
    Examples:
      rocotoviewer monitor /path/to/workflows               # Monitor directory (positional)
      rocotoviewer monitor workflow.xml                     # Monitor workflow (positional)
      rocotoviewer monitor -d /path/to/workflows            # Monitor directory
      rocotoviewer monitor -w workflow.xml -i 5             # Monitor workflow with 5s interval
      rocotoviewer monitor -d /workflows --format json      # Output in JSON format
      rocotoviewer monitor -d /workflows -o results.json    # Save results to file
    """
    if verbose == 1:
        os.environ['ROCOTOVIEWER_LOG_LEVEL'] = 'INFO'
    elif verbose >= 2:
        os.environ['ROCOTOVIEWER_LOG_LEVEL'] = 'DEBUG'
    
    # Handle positional argument
    if path_arg:
        if path_arg.is_dir():
            directory = path_arg
        elif path_arg.is_file():
            workflow = path_arg
    
    exit_code = run_monitor(config_path=config, directory=directory,
                           workflow_path=workflow, interval=interval,
                           output_path=output, output_format=format,
                           follow=follow)
    sys.exit(exit_code)


@cli.command(help="Parse a workflow file and extract data.")
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Path to configuration file')
@click.argument('workflow_path', type=click.Path(exists=True, path_type=Path))
@click.option('--output', '-o', type=click.Path(path_type=Path),
              help='Output file for parsed results')
@click.option('--format', type=click.Choice(['json', 'yaml', 'csv', 'text']),
              default='json', help='Output format (default: json)')
@click.option('--extract', '-e', multiple=True,
              help='Specific data to extract (tasks, cycles, resources, dependencies)')
@click.option('--verbose', '-V', count=True, help='Increase verbosity (use -VV for debug)')
def parse(config: Optional[Path], workflow_path: Path, output: Optional[Path],
         format: str, extract: List[str], verbose: int) -> None:
    """
    Parse a workflow file and extract data.
    
    This command parses a Rocoto workflow XML file and extracts structured data
    in various formats. You can specify which data elements to extract or
    get the complete workflow structure.
    
    Examples:
      rocotoviewer parse workflow.xml                           # Parse and output as JSON
      rocotoviewer parse workflow.xml --format yaml             # Output as YAML
      rocotoviewer parse workflow.xml -o results.json           # Save to file
      rocotoviewer parse workflow.xml -e tasks -e cycles        # Extract only tasks and cycles
      rocotoviewer parse workflow.xml --format csv              # Output as CSV (where applicable)
    """
    if verbose == 1:
        os.environ['ROCOTOVIEWER_LOG_LEVEL'] = 'INFO'
    elif verbose >= 2:
        os.environ['ROCOTOVIEWER_LOG_LEVEL'] = 'DEBUG'
    
    exit_code = run_parse(config_path=config, workflow_path=workflow_path,
                         output_path=output, output_format=format,
                         extract_fields=list(extract))
    sys.exit(exit_code)


@cli.command(help="Show statistics and summary for workflow(s).")
@click.option('--config', '-c', type=click.Path(exists=True, path_type=Path),
              help='Path to configuration file')
@click.argument('workflow_paths', type=click.Path(exists=True, path_type=Path), nargs=-1, required=False)
@click.option('--output', '-o', type=click.Path(path_type=Path),
              help='Output file for statistics')
@click.option('--format', type=click.Choice(['json', 'yaml', 'csv', 'text']),
              default='text', help='Output format (default: text)')
@click.option('--verbose', '-V', count=True, help='Increase verbosity (use -VV for debug)')
def stats(config: Optional[Path], workflow_paths: List[Path],
         output: Optional[Path], format: str, verbose: int) -> None:
    """
    Show statistics and summary for workflow(s).
    
    This command analyzes workflow files and provides comprehensive statistics
    including task counts, status distributions, cycle information, and more.
    If no workflow path is provided, it will analyze all workflows in the config.
    
    Examples:
      rocotoviewer stats workflow.xml                    # Show stats for workflow
      rocotoviewer stats workflow.xml --format json      # Output stats as JSON
      rocotoviewer stats -o stats.txt                    # Save stats to file
      rocotoviewer stats -c config.yaml                  # Use specific config
    """
    if verbose == 1:
        os.environ['ROCOTOVIEWER_LOG_LEVEL'] = 'INFO'
    elif verbose >= 2:
        os.environ['ROCOTOVIEWER_LOG_LEVEL'] = 'DEBUG'
    
    # Convert multiple workflow paths to single path if only one, or handle multiple
    if workflow_paths:
        if len(workflow_paths) == 1:
            workflow_path = workflow_paths[0]
        else:
            # For multiple paths, we'll pass the first one and let the function handle multiple
            # This is a limitation of the current run_stats implementation
            workflow_path = workflow_paths[0]
    else:
        workflow_path = None
    
    exit_code = run_stats(config_path=config, workflow_path=workflow_path,
                         output_path=output, output_format=format)
    sys.exit(exit_code)


@cli.command('config', help="Manage configuration settings.")
@click.option('--config', '-c', type=click.Path(path_type=Path),
              help='Path to configuration file (default: rocoto_config.yaml)')
@click.option('--set', 'set_options', multiple=True, nargs=2, metavar='KEY VALUE',
              help='Set configuration option (e.g., --set display.theme dark)')
@click.option('--get', 'get_option', type=str,
              help='Get specific configuration option')
@click.option('--list', 'list_config', is_flag=True,
              help='List all configuration options')
@click.option('--validate', 'validate_config', is_flag=True,
              help='Validate configuration file')
@click.option('--reset', 'reset_config', is_flag=True,
              help='Reset to default configuration')
@click.option('--verbose', '-V', count=True, help='Increase verbosity (use -VV for debug)')
def config_cmd(config: Optional[Path], set_options: List[tuple],
              get_option: str, list_config: bool, validate_config: bool,
              reset_config: bool, verbose: int) -> None:
    """
    Manage configuration settings.
    
    This command allows you to view, modify, validate, and manage RocotoViewer
    configuration settings. You can set individual options, view the current
    configuration, validate the configuration file, or reset to defaults.
    
    Configuration options follow the format 'section.option', such as:
    - display.theme
    - display.refresh_interval
    - monitor.enabled
    - logging.level
    
    Examples:
      rocotoviewer config --list                           # List all config options
      rocotoviewer config --get display.theme             # Get specific option
      rocotoviewer config --set display.theme dark        # Set an option
      rocotoviewer config --validate                      # Validate config
      rocotoviewer config --reset                         # Reset to defaults
      rocotoviewer config --set logging.level DEBUG       # Set logging level
    """
    if verbose == 1:
        os.environ['ROCOTOVIEWER_LOG_LEVEL'] = 'INFO'
    elif verbose >= 2:
        os.environ['ROCOTOVIEWER_LOG_LEVEL'] = 'DEBUG'
    
    exit_code = run_config_commands(config_path=config, set_options=list(set_options),
                                   get_option=get_option, list_config=list_config,
                                   validate_config=validate_config,
                                   reset_config=reset_config)
    sys.exit(exit_code)


@cli.command(help="Initialize a new configuration file.")
def init() -> None:
    """
    Initialize a new configuration file.
    
    Creates a default rocoto_config.yaml file in the current directory
    with sensible defaults for getting started with RocotoViewer.
    
    Example:
      rocotoviewer init    # Create default configuration
    """
    config_path = Path("rocoto_config.yaml")
    if config_path.exists():
        click.echo(f"Configuration file already exists: {config_path}", err=True)
        sys.exit(1)
    
    default_config = Config.get_default_config_dict()
    
    with open(config_path, 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False)
    
    click.echo(f"Created default configuration file: {config_path}")


def main() -> None:
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()