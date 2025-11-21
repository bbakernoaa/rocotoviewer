"""
Main application entry point for RocotoViewer.

This module provides the primary application interface and can be used
to launch the UI or run in headless mode for monitoring workflows.
"""

import sys
import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import json
import yaml
from datetime import datetime

from .ui.app import RocotoViewerApp
from .config.config import Config
from .core.log_processor import LogProcessor
from .core.file_monitor import FileMonitor
from .core.state_manager import StateManager
from .parsers.workflow_parser import WorkflowParser


def setup_logging(log_level: str = "INFO", log_file: Optional[Path] = None) -> None:
    """Setup logging for the application."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(logging.Formatter(log_format))
        logging.getLogger().addHandler(file_handler)


def run_app(config_path: Optional[Path] = None, workflow_path: Optional[Path] = None, 
           database_path: Optional[Path] = None, log_paths: Optional[List[Path]] = None,
           theme: Optional[str] = None, follow: bool = False, filter_str: Optional[str] = None) -> int:
    """
    Run the main application.
    
    Args:
        config_path: Path to configuration file
        workflow_path: Path to workflow file to view
        database_path: Path to database file
        log_paths: List of paths to log files to monitor
        theme: UI theme to use
        follow: Auto-follow workflow changes
        filter_str: Filter for tasks by status or name
        
    Returns:
        Exit code
    """
    try:
        # Load configuration
        config = Config.load(config_path)
        
        # Override configuration with CLI options if provided
        if theme:
            config.display.theme = theme
        
        # Set logging level from environment if available
        log_level = "INFO"
        if 'ROCOTOVIEWER_LOG_LEVEL' in os.environ:
            log_level = os.environ['ROCOTOVIEWER_LOG_LEVEL']
        
        setup_logging(log_level, Path(config.logging.file) if config.logging.file else None)
        
        # Initialize core components
        state_manager = StateManager(config)
        log_processor = LogProcessor(config)
        file_monitor = FileMonitor(config, state_manager)
        workflow_parser = WorkflowParser(config)
        
        # Add log files to monitor if provided
        if log_paths:
            for log_path in log_paths:
                file_monitor.add_log_file_for_tailing(log_path)
        
        # Start file monitoring if enabled
        if config.monitor.enabled:
            file_monitor.start()
        
        # Load workflow if provided
        if workflow_path:
            try:
                workflow_data = workflow_parser.parse(str(workflow_path))
                workflow_id = workflow_data.get('id', 'unknown')
                
                # Update state with new workflow
                state_manager.update_workflow(workflow_id, workflow_data)
            except Exception as e:
                logging.error(f"Error loading workflow {workflow_path}: {str(e)}")
        
        # Launch UI application
        app = RocotoViewerApp(config, state_manager, log_processor, workflow_parser)
        app.run()
        
        return 0
        
    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        return 1
    finally:
        # Cleanup resources
        if 'file_monitor' in locals():
            file_monitor.stop()


def run_monitor(config_path: Optional[Path] = None, directory: Optional[Path] = None, 
               workflow_path: Optional[Path] = None, interval: int = 10,
               output_path: Optional[Path] = None, output_format: str = 'text',
               follow: bool = True) -> int:
    """
    Run monitoring mode to track workflow changes.
    
    Args:
        config_path: Path to configuration file
        directory: Directory to monitor for workflow files
        workflow_path: Specific workflow file to monitor
        interval: Polling interval in seconds
        output_path: Output file for monitoring results
        output_format: Output format ('json', 'yaml', 'csv', 'text')
        follow: Continue monitoring indefinitely
        
    Returns:
        Exit code
    """
    try:
        config = Config.load(config_path)
        
        # Set logging level from environment if available
        log_level = "INFO"
        if 'ROCOTOVIEWER_LOG_LEVEL' in os.environ:
            log_level = os.environ['ROCOTOVIEWER_LOG_LEVEL']
        
        setup_logging(log_level, Path(config.logging.file) if config.logging.file else None)
        
        # Initialize monitoring components
        state_manager = StateManager(config)
        file_monitor = FileMonitor(config, state_manager)
        
        # Set up monitoring paths
        if directory:
            file_monitor.add_path(directory)
        elif workflow_path:
            file_monitor.add_path(workflow_path.parent)
        
        # Start monitoring
        file_monitor.start()
        
        # For now, just run for a short period to demonstrate functionality
        # In a real implementation, this would run continuously based on follow flag
        import time
        time.sleep(5)  # Short demo period
        
        # Generate output if requested
        if output_path:
            workflows = state_manager.get_all_workflows()
            results = {
                'timestamp': datetime.now().isoformat(),
                'workflows': workflows,
                'directory': str(directory) if directory else None,
                'workflow': str(workflow_path) if workflow_path else None
            }
            
            with open(output_path, 'w') as f:
                if output_format == 'json':
                    json.dump(results, f, indent=2)
                elif output_format == 'yaml':
                    yaml.dump(results, f, default_flow_style=False)
                elif output_format == 'text':
                    f.write(f"Monitoring Results - {results['timestamp']}\n")
                    f.write(f"Workflows found: {len(results['workflows'])}\n")
                    for wf_id, wf_data in results['workflows'].items():
                        f.write(f"  - {wf_id}: {wf_data.get('status', 'unknown')}\n")
        
        return 0
        
    except Exception as e:
        logging.error(f"Monitor error: {str(e)}")
        return 1
    finally:
        # Cleanup resources
        if 'file_monitor' in locals():
            file_monitor.stop()


def run_parse(config_path: Optional[Path] = None, workflow_path: Optional[Path] = None,
             output_path: Optional[Path] = None, output_format: str = 'json',
             extract_fields: Optional[List[str]] = None) -> int:
    """
    Run parse mode to extract data from workflow files.
    
    Args:
        config_path: Path to configuration file
        workflow_path: Path to workflow file to parse
        output_path: Output file for parsed results
        output_format: Output format ('json', 'yaml', 'csv', 'text')
        extract_fields: Specific fields to extract
        
    Returns:
        Exit code
    """
    try:
        config = Config.load(config_path) if config_path else Config()
        
        # Set logging level from environment if available
        log_level = "INFO"
        if 'ROCOTOVIEWER_LOG_LEVEL' in os.environ:
            log_level = os.environ['ROCOTOVIEWER_LOG_LEVEL']
        
        setup_logging(log_level, Path(config.logging.file) if config.logging.file else None)
        
        # Parse the workflow
        parser = WorkflowParser(config)
        workflow_data = parser.parse(str(workflow_path))
        
        # Extract specific fields if requested
        if extract_fields:
            extracted_data = {}
            for field in extract_fields:
                if field in workflow_data:
                    extracted_data[field] = workflow_data[field]
                elif field == 'tasks':
                    extracted_data['tasks'] = workflow_data.get('tasks', [])
                elif field == 'cycles':
                    extracted_data['cycles'] = workflow_data.get('cycles', [])
                elif field == 'resources':
                    extracted_data['resources'] = workflow_data.get('resources', [])
                elif field == 'dependencies':
                    extracted_data['dependencies'] = workflow_data.get('dependencies', [])
        else:
            extracted_data = workflow_data
        
        # Output results
        if output_path:
            with open(output_path, 'w') as f:
                if output_format == 'json':
                    json.dump(extracted_data, f, indent=2)
                elif output_format == 'yaml':
                    yaml.dump(extracted_data, f, default_flow_style=False)
                elif output_format == 'text':
                    f.write(f"Workflow: {workflow_data.get('id', 'unknown')}\n")
                    f.write(f"Name: {workflow_data.get('name', 'N/A')}\n")
                    f.write(f"Tasks: {len(workflow_data.get('tasks', []))}\n")
                    f.write(f"Cycles: {len(workflow_data.get('cycles', []))}\n")
                    f.write(f"Resources: {len(workflow_data.get('resources', []))}\n")
        else:
            # Print to stdout
            if output_format == 'json':
                print(json.dumps(extracted_data, indent=2))
            elif output_format == 'yaml':
                print(yaml.dump(extracted_data, default_flow_style=False))
            elif output_format == 'text':
                print(f"Workflow: {workflow_data.get('id', 'unknown')}")
                print(f"Name: {workflow_data.get('name', 'N/A')}")
                print(f"Tasks: {len(workflow_data.get('tasks', []))}")
                print(f"Cycles: {len(workflow_data.get('cycles', []))}")
                print(f"Resources: {len(workflow_data.get('resources', []))}")
        
        return 0
        
    except Exception as e:
        logging.error(f"Parse error: {str(e)}")
        return 1


def run_stats(config_path: Optional[Path] = None, workflow_path: Optional[Path] = None,
             output_path: Optional[Path] = None, output_format: str = 'text') -> int:
    """
    Run stats mode to show workflow statistics.
    
    Args:
        config_path: Path to configuration file
        workflow_path: Path to workflow file to analyze (optional, if None uses all workflows from config)
        output_path: Output file for statistics
        output_format: Output format ('json', 'yaml', 'csv', 'text')
        
    Returns:
        Exit code
    """
    try:
        config = Config.load(config_path) if config_path else Config()
        
        # Set logging level from environment if available
        log_level = "INFO"
        if 'ROCOTOVIEWER_LOG_LEVEL' in os.environ:
            log_level = os.environ['ROCOTOVIEWER_LOG_LEVEL']
        
        setup_logging(log_level, Path(config.logging.file) if config.logging.file else None)
        
        # Initialize components to get workflow data
        state_manager = StateManager(config)
        workflow_parser = WorkflowParser(config)
        
        # If specific workflow path(s) are provided, parse them
        workflows = {}
        if workflow_path:
            # Handle single workflow path
            workflow_data = workflow_parser.parse(str(workflow_path))
            workflow_id = workflow_data.get('id', 'unknown')
            state_manager.update_workflow(workflow_id, workflow_data)
            workflows[workflow_id] = state_manager.get_workflow(workflow_id)
        else:
            # Use workflows from config
            for wf_config in config.workflows:
                wf_path = Path(wf_config['path'])
                if wf_path.exists() and wf_path.is_file():
                    wf_data = workflow_parser.parse(str(wf_path))
                    wf_id = wf_data.get('id', wf_path.stem)
                    state_manager.update_workflow(wf_id, wf_data)
                    workflows[wf_id] = state_manager.get_workflow(wf_id)
        
        # Calculate statistics
        total_workflows = len(workflows)
        total_tasks = 0
        status_counts = {}
        total_cycles = 0
        total_resources = 0
        
        for wf_id, wf_data in workflows.items():
            wf_tasks = wf_data.get('data', {}).get('tasks', [])
            total_tasks += len(wf_tasks)
            
            # Count task statuses
            for task in wf_tasks:
                status = task.get('status', 'unknown').lower()
                status_counts[status] = status_counts.get(status, 0) + 1
            
            total_cycles += len(wf_data.get('data', {}).get('cycles', []))
            total_resources += len(wf_data.get('data', {}).get('resources', []))
        
        stats = {
            'timestamp': datetime.now().isoformat(),
            'workflows': {
                'total': total_workflows,
                'active': len([wf for wf in workflows.values() if wf.get('status') in ['running', 'active', 'R', 'Q']]),
                'completed': len([wf for wf in workflows.values() if wf.get('status') in ['success', 'completed', 'S']]),
                'failed': len([wf for wf in workflows.values() if wf.get('status') in ['failed', 'F']])
            },
            'tasks': {
                'total': total_tasks,
                'by_status': status_counts
            },
            'cycles': total_cycles,
            'resources': total_resources
        }
        
        # Output results
        if output_path:
            with open(output_path, 'w') as f:
                if output_format == 'json':
                    json.dump(stats, f, indent=2)
                elif output_format == 'yaml':
                    yaml.dump(stats, f, default_flow_style=False)
                elif output_format == 'text':
                    f.write(f"Workflow Statistics - {stats['timestamp']}\n")
                    f.write(f"Workflows: {stats['workflows']['total']} (Active: {stats['workflows']['active']}, Completed: {stats['workflows']['completed']}, Failed: {stats['workflows']['failed']})\n")
                    f.write(f"Tasks: {stats['tasks']['total']}\n")
                    for status, count in stats['tasks']['by_status'].items():
                        f.write(f" {status}: {count}\n")
                    f.write(f"Cycles: {stats['cycles']}\n")
                    f.write(f"Resources: {stats['resources']}\n")
        else:
            # Print to stdout
            if output_format == 'json':
                print(json.dumps(stats, indent=2))
            elif output_format == 'yaml':
                print(yaml.dump(stats, default_flow_style=False))
            elif output_format == 'text':
                print(f"Workflow Statistics - {stats['timestamp']}")
                print(f"Workflows: {stats['workflows']['total']} (Active: {stats['workflows']['active']}, Completed: {stats['workflows']['completed']}, Failed: {stats['workflows']['failed']})")
                print(f"Tasks: {stats['tasks']['total']}")
                for status, count in stats['tasks']['by_status'].items():
                    print(f"  {status}: {count}")
                print(f"Cycles: {stats['cycles']}")
                print(f"Resources: {stats['resources']}")
        
        return 0
        
    except Exception as e:
        logging.error(f"Stats error: {str(e)}")
        return 1


def run_config_commands(config_path: Optional[Path] = None, set_options: Optional[List[tuple]] = None,
                       get_option: Optional[str] = None, list_config: bool = False,
                       validate_config: bool = False, reset_config: bool = False) -> int:
    """
    Run configuration management commands.
    
    Args:
        config_path: Path to configuration file
        set_options: List of (key, value) tuples to set
        get_option: Option to get
        list_config: Whether to list all configuration options
        validate_config: Whether to validate the configuration
        reset_config: Whether to reset to default configuration
        
    Returns:
        Exit code
    """
    try:
        # Determine config path (use default if not provided)
        if not config_path:
            config_path = Path("rocoto_config.yaml")
            if not config_path.exists():
                config_path = Path.home() / ".rocotoviewer" / "config.yaml"
        
        # Set logging level from environment if available
        log_level = "INFO"
        if 'ROCOTOVIEWER_LOG_LEVEL' in os.environ:
            log_level = os.environ['ROCOTOVIEWER_LOG_LEVEL']
        
        setup_logging(log_level)
        
        if reset_config:
            # Reset to default configuration
            default_config = Config()
            default_config.save(config_path)
            print(f"Configuration reset to defaults: {config_path}")
            return 0
        
        # Load existing config
        config = Config.load(config_path)
        
        if validate_config:
            # Validate configuration (basic check)
            if not hasattr(config, 'workflows') or not hasattr(config, 'display'):
                print("Configuration validation failed: Missing required sections", file=sys.stderr)
                return 1
            print("Configuration is valid")
            return 0
        
        if set_options:
            # Set configuration options
            for key, value in set_options:
                # Parse the key to determine the configuration section and option
                parts = key.split('.')
                if len(parts) == 2:
                    section, option = parts
                    if hasattr(config, section):
                        section_obj = getattr(config, section)
                        if hasattr(section_obj, option):
                            # Convert value to appropriate type based on current value
                            current_value = getattr(section_obj, option)
                            if isinstance(current_value, bool):
                                value = value.lower() in ['true', '1', 'yes', 'on']
                            elif isinstance(current_value, int):
                                value = int(value)
                            elif isinstance(current_value, float):
                                value = float(value)
                            setattr(section_obj, option, value)
                        else:
                            print(f"Unknown option: {option} in section {section}", file=sys.stderr)
                            return 1
                    else:
                        print(f"Unknown section: {section}", file=sys.stderr)
                        return 1
                else:
                    print(f"Invalid option format: {key}. Use 'section.option' format", file=sys.stderr)
                    return 1
            
            # Save the updated configuration
            config.save(config_path)
            print(f"Configuration updated: {config_path}")
        
        if get_option:
            # Get specific configuration option
            parts = get_option.split('.')
            if len(parts) == 2:
                section, option = parts
                if hasattr(config, section):
                    section_obj = getattr(config, section)
                    if hasattr(section_obj, option):
                        value = getattr(section_obj, option)
                        print(f"{get_option} = {value}")
                    else:
                        print(f"Unknown option: {option} in section {section}", file=sys.stderr)
                        return 1
                else:
                    print(f"Unknown section: {section}", file=sys.stderr)
                    return 1
            else:
                print(f"Invalid option format: {get_option}. Use 'section.option' format", file=sys.stderr)
                return 1
        
        if list_config:
            # List all configuration options
            config_dict = config.to_dict()
            print("Configuration:")
            for section, options in config_dict.items():
                print(f"  [{section}]")
                if isinstance(options, dict):
                    for key, value in options.items():
                        print(f"    {key} = {value}")
                else:
                    print(f"    {section} = {options}")
                print()
        
        return 0
        
    except Exception as e:
        logging.error(f"Config command error: {str(e)}")
        return 1


def main() -> None:
    """Main entry point for the application."""
    # This function is typically called from the CLI
    # For direct execution, use default configuration
    exit_code = run_app()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()