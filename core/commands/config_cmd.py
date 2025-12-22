
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from config.config import Config
from utils.log_setup import setup_logging


def run_config_commands(config_path: Optional[Path] = None, set_options: Optional[List[tuple]] = None,
                        get_option: Optional[str] = None, list_config: bool = False,
                        validate_config: bool = False, reset_config: bool = False) -> int:
    """
    Run configuration management commands.
    """
    try:
        if not config_path:
            config_path = Path("rocoto_config.yaml")
            if not config_path.exists():
                config_path = Path.home() / ".rocotoviewer" / "config.yaml"

        log_level = os.environ.get('ROCOTOVIEWER_LOG_LEVEL', "INFO")
        setup_logging(log_level)

        if reset_config:
            default_config = Config()
            default_config.save(config_path)
            print(f"Configuration reset to defaults: {config_path}")
            return 0

        config = Config.load(config_path)

        if validate_config:
            if not hasattr(config, 'workflows') or not hasattr(config, 'display'):
                print("Configuration validation failed: Missing required sections", file=sys.stderr)
                return 1
            print("Configuration is valid")
            return 0

        if set_options:
            for key, value in set_options:
                parts = key.split('.')
                if len(parts) == 2:
                    section, option = parts
                    if hasattr(config, section):
                        section_obj = getattr(config, section)
                        if hasattr(section_obj, option):
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

            config.save(config_path)
            print(f"Configuration updated: {config_path}")

        if get_option:
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
        logging.error(f"Config command error: {e}")
        return 1
