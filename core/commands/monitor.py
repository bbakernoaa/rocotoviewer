
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from config.config import Config
from core.file_monitor import FileMonitor
from core.state_manager import StateManager
from utils.log_setup import setup_logging


def run_monitor(config_path: Optional[Path] = None, directory: Optional[Path] = None,
                workflow_path: Optional[Path] = None, interval: int = 10,
                output_path: Optional[Path] = None, output_format: str = 'text',
                follow: bool = True) -> int:
    """
    Run monitoring mode to track workflow changes.
    """
    try:
        config = Config.load(config_path)

        log_level = os.environ.get('ROCOTOVIEWER_LOG_LEVEL', "INFO")
        setup_logging(log_level, Path(config.logging.file) if config.logging.file else None)

        state_manager = StateManager(config)
        file_monitor = FileMonitor(config, state_manager)

        if directory:
            file_monitor.add_path(directory)
        elif workflow_path:
            file_monitor.add_path(workflow_path.parent)

        file_monitor.start()

        time.sleep(5)

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
        logging.error(f"Monitor error: {e}")
        return 1
    finally:
        if 'file_monitor' in locals():
            file_monitor.stop()
