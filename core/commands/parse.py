
import json
import logging
import os
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

import yaml

from config.config import Config
from parsers.workflow_parser import WorkflowParser
from utils.log_setup import setup_logging


def run_parse(config_path: Optional[Path] = None, workflow_path: Optional[Path] = None,
              output_path: Optional[Path] = None, output_format: str = 'json',
              extract_fields: Optional[List[str]] = None) -> int:
    """
    Run parse mode to extract data from workflow files.
    """
    try:
        config = Config.load(config_path) if config_path else Config()

        log_level = os.environ.get('ROCOTOVIEWER_LOG_LEVEL', "INFO")
        setup_logging(log_level, Path(config.logging.file) if config.logging.file else None)

        parser = WorkflowParser(config)
        workflow = parser.parse(str(workflow_path))

        if not workflow:
            logging.error(f"Failed to parse workflow: {workflow_path}")
            return 1

        workflow_data = asdict(workflow)

        if extract_fields:
            extracted_data = {field: workflow_data.get(field) for field in extract_fields}
        else:
            extracted_data = workflow_data

        if output_path:
            with open(output_path, 'w') as f:
                if output_format == 'json':
                    json.dump(extracted_data, f, indent=2)
                elif output_format == 'yaml':
                    yaml.dump(extracted_data, f, default_flow_style=False)
                elif output_format == 'text':
                    f.write(f"Workflow: {workflow.id}\n")
                    f.write(f"Name: {workflow.name}\n")
                    f.write(f"Tasks: {len(workflow.tasks)}\n")
        else:
            if output_format == 'json':
                print(json.dumps(extracted_data, indent=2))
            elif output_format == 'yaml':
                print(yaml.dump(extracted_data, default_flow_style=False))
            elif output_format == 'text':
                print(f"Workflow: {workflow.id}")
                print(f"Name: {workflow.name}")
                print(f"Tasks: {len(workflow.tasks)}")

        return 0

    except Exception as e:
        logging.error(f"Parse error: {e}")
        return 1
