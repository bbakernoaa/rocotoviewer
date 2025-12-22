
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from config.config import Config
from core.state_manager import StateManager
from parsers.workflow_parser import WorkflowParser
from utils.log_setup import setup_logging


def run_stats(config_path: Optional[Path] = None, workflow_path: Optional[Path] = None,
              output_path: Optional[Path] = None, output_format: str = 'text') -> int:
    """
    Run stats mode to show workflow statistics.
    """
    try:
        config = Config.load(config_path) if config_path else Config()

        log_level = os.environ.get('ROCOTOVIEWER_LOG_LEVEL', "INFO")
        setup_logging(log_level, Path(config.logging.file) if config.logging.file else None)

        state_manager = StateManager(config)
        workflow_parser = WorkflowParser(config)

        workflows = []
        if workflow_path:
            workflow = workflow_parser.parse(str(workflow_path))
            if workflow:
                workflows.append(workflow)
        else:
            for wf_config in config.workflows:
                wf_path = Path(wf_config['path'])
                if wf_path.exists() and wf_path.is_file():
                    workflow = workflow_parser.parse(str(wf_path))
                    if workflow:
                        workflows.append(workflow)

        total_workflows = len(workflows)
        total_tasks = 0
        status_counts = {}
        total_cycles = 0
        total_resources = 0

        for workflow in workflows:
            total_tasks += len(workflow.tasks)
            total_cycles += len(workflow.cycles)
            total_resources += len(workflow.resources)

            for task in workflow.tasks:
                status = task.attributes.get('status', 'unknown').lower()
                status_counts[status] = status_counts.get(status, 0) + 1

        stats = {
            'timestamp': datetime.now().isoformat(),
            'workflows': {
                'total': total_workflows,
                'active': len([wf for wf in workflows if wf.status in ['running', 'active', 'R', 'Q']]),
                'completed': len([wf for wf in workflows if wf.status in ['success', 'completed', 'S']]),
                'failed': len([wf for wf in workflows if wf.status in ['failed', 'F']])
            },
            'tasks': {
                'total': total_tasks,
                'by_status': status_counts
            },
            'cycles': total_cycles,
            'resources': total_resources
        }

        if output_path:
            with open(output_path, 'w') as f:
                if output_format == 'json':
                    json.dump(stats, f, indent=2)
                elif output_format == 'yaml':
                    yaml.dump(stats, f, default_flow_style=False)
                elif output_format == 'text':
                    f.write(f"Workflow Statistics - {stats['timestamp']}\n")
                    f.write(
                        f"Workflows: {stats['workflows']['total']} (Active: {stats['workflows']['active']}, Completed: {stats['workflows']['completed']}, Failed: {stats['workflows']['failed']})\n")
                    f.write(f"Tasks: {stats['tasks']['total']}\n")
                    for status, count in stats['tasks']['by_status'].items():
                        f.write(f" {status}: {count}\n")
                    f.write(f"Cycles: {stats['cycles']}\n")
                    f.write(f"Resources: {stats['resources']}\n")
        else:
            if output_format == 'json':
                print(json.dumps(stats, indent=2))
            elif output_format == 'yaml':
                print(yaml.dump(stats, default_flow_style=False))
            elif output_format == 'text':
                print(f"Workflow Statistics - {stats['timestamp']}")
                print(
                    f"Workflows: {stats['workflows']['total']} (Active: {stats['workflows']['active']}, Completed: {stats['workflows']['completed']}, Failed: {stats['workflows']['failed']})")
                print(f"Tasks: {stats['tasks']['total']}")
                for status, count in stats['tasks']['by_status'].items():
                    print(f"  {status}: {count}")
                print(f"Cycles: {stats['cycles']}")
                print(f"Resources: {stats['resources']}")

        return 0

    except Exception as e:
        logging.error(f"Stats error: {e}")
        return 1
