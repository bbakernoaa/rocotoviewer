
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from config.config import Config
from core.file_monitor import FileMonitor
from core.log_processor import StreamingLogProcessor
from core.state_manager import StateManager
from parsers.workflow_parser import WorkflowParser
from ui.app import RocotoViewerApp
from utils.log_setup import setup_logging


def run_app(config_path: Optional[Path] = None, workflow_path: Optional[Path] = None,
            database_path: Optional[Path] = None, log_paths: Optional[List[Path]] = None,
            theme: Optional[str] = None, follow: bool = False, filter_str: Optional[str] = None) -> int:
    """
    Run the main application.
    """
    try:
        config = Config.load(config_path)

        if theme:
            config.display.theme = theme

        log_level = os.environ.get('ROCOTOVIEWER_LOG_LEVEL', "INFO")
        setup_logging(log_level, Path(config.logging.file) if config.logging.file else None)

        state_manager = StateManager(config)
        log_processor = StreamingLogProcessor(config)
        file_monitor = FileMonitor(config, state_manager)
        workflow_parser = WorkflowParser(config)

        if log_paths:
            for log_path in log_paths:
                file_monitor.add_log_file_for_tailing(log_path)

        if config.monitor.enabled:
            file_monitor.start()

        if workflow_path:
            try:
                workflow = workflow_parser.parse(str(workflow_path))
                if workflow:
                    state_manager.update_workflow(workflow.id, workflow)
            except Exception as e:
                logging.error(f"Error loading workflow {workflow_path}: {e}")

        app = RocotoViewerApp(config, state_manager, log_processor, workflow_parser)
        app.run()

        return 0

    except Exception as e:
        logging.error(f"Application error: {e}")
        return 1
    finally:
        if 'file_monitor' in locals():
            file_monitor.stop()
