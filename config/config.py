"""
Configuration management for RocotoViewer.

This module provides classes and methods for loading, validating,
and managing application configuration with CLI integration support.
"""

import yaml
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict, field
from .settings import Settings


@dataclass
class WorkflowConfig:
    """Configuration for a single workflow."""
    path: str
    name: str
    monitor: bool = True


@dataclass
class DisplayConfig:
    """Configuration for display settings."""
    theme: str = "default"
    refresh_interval: int = 5  # seconds
    max_log_lines: int = 1000


@dataclass
class MonitorConfig:
    """Configuration for file monitoring."""
    enabled: bool = True
    poll_interval: int = 10  # seconds
    max_file_size: int = 10485760  # 10MB in bytes


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    file: Optional[str] = None


@dataclass
class Config:
    """Main configuration class for RocotoViewer."""
    workflows: List[Dict[str, Any]] = field(default_factory=list)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def __post_init__(self):
        # Environment variable overrides
        if os.getenv('ROCOTOVIEWER_THEME'):
            self.display.theme = os.getenv('ROCOTOVIEWER_THEME')
        if os.getenv('ROCOTOVIEWER_REFRESH_INTERVAL'):
            self.display.refresh_interval = int(os.getenv('ROCOTOVIEWER_REFRESH_INTERVAL', 5))
        if os.getenv('ROCOTOVIEWER_LOG_LEVEL'):
            self.logging.level = os.getenv('ROCOTOVIEWER_LOG_LEVEL')
        if os.getenv('ROCOTOVIEWER_POLL_INTERVAL'):
            self.monitor.poll_interval = int(os.getenv('ROCOTOVIEWER_POLL_INTERVAL', 10))

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> 'Config':
        """
        Load configuration from a YAML file or return default configuration.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Config instance
        """
        # Check for config path in environment if not provided
        if not config_path:
            env_config_path = os.getenv('ROCOTOVIEWER_CONFIG')
            if env_config_path:
                config_path = Path(env_config_path)
        
        if config_path and config_path.exists():
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
                if data is None:
                    data = {}
                return cls.from_dict(data)
        else:
            # Return default configuration
            return cls()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """
        Create Config instance from dictionary.
        
        Args:
            data: Configuration dictionary
            
        Returns:
            Config instance
        """
        config_data = data.copy()
        
        # Process display config
        if 'display' in config_data:
            display_data = config_data['display']
            config_data['display'] = DisplayConfig(**display_data) if isinstance(display_data, dict) else DisplayConfig()
        else:
            config_data['display'] = DisplayConfig()
        
        # Process monitor config
        if 'monitor' in config_data:
            monitor_data = config_data['monitor']
            config_data['monitor'] = MonitorConfig(**monitor_data) if isinstance(monitor_data, dict) else MonitorConfig()
        else:
            config_data['monitor'] = MonitorConfig()
        
        # Process logging config
        if 'logging' in config_data:
            logging_data = config_data['logging']
            config_data['logging'] = LoggingConfig(**logging_data) if isinstance(logging_data, dict) else LoggingConfig()
        else:
            config_data['logging'] = LoggingConfig()
        
        # Process workflows
        if 'workflows' not in config_data:
            config_data['workflows'] = []
        
        return cls(**config_data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert Config instance to dictionary.
        
        Returns:
            Configuration dictionary
        """
        result = asdict(self)
        # Convert dataclass instances to dictionaries recursively
        if hasattr(self.display, '__dict__'):
            result['display'] = asdict(self.display)
        if hasattr(self.monitor, '__dict__'):
            result['monitor'] = asdict(self.monitor)
        if hasattr(self.logging, '__dict__'):
            result['logging'] = asdict(self.logging)
        return result

    def save(self, config_path: Path) -> None:
        """
        Save configuration to a YAML file.
        
        Args:
            config_path: Path to save configuration file
        """
        with open(config_path, 'w') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)

    def validate(self) -> List[str]:
        """
        Validate the configuration and return a list of errors.
        
        Returns:
            List of validation errors, empty if valid
        """
        errors = []
        
        # Validate workflow paths
        for i, wf_config in enumerate(self.workflows):
            if 'path' in wf_config:
                wf_path = Path(wf_config['path'])
                if not wf_path.exists():
                    errors.append(f"Workflow path does not exist: {wf_path} (workflow {i})")
        
        # Validate display settings
        if self.display.refresh_interval <= 0:
            errors.append("Display refresh interval must be positive")
        if self.display.max_log_lines <= 0:
            errors.append("Display max log lines must be positive")
        
        # Validate monitor settings
        if self.monitor.poll_interval <= 0:
            errors.append("Monitor poll interval must be positive")
        if self.monitor.max_file_size <= 0:
            errors.append("Monitor max file size must be positive")
        
        # Validate logging level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.logging.level.upper() not in valid_log_levels:
            errors.append(f"Invalid logging level: {self.logging.level}. Valid values: {', '.join(valid_log_levels)}")
        
        return errors

    def get_env_overrides(self) -> Dict[str, Any]:
        """
        Get configuration values that are overridden by environment variables.
        
        Returns:
            Dictionary of environment variable overrides
        """
        overrides = {}
        
        if os.getenv('ROCOTOVIEWER_THEME'):
            overrides['display.theme'] = os.getenv('ROCOTOVIEWER_THEME')
        if os.getenv('ROCOTOVIEWER_REFRESH_INTERVAL'):
            overrides['display.refresh_interval'] = int(os.getenv('ROCOTOVIEWER_REFRESH_INTERVAL'))
        if os.getenv('ROCOTOVIEWER_LOG_LEVEL'):
            overrides['logging.level'] = os.getenv('ROCOTOVIEWER_LOG_LEVEL')
        if os.getenv('ROCOTOVIEWER_POLL_INTERVAL'):
            overrides['monitor.poll_interval'] = int(os.getenv('ROCOTOVIEWER_POLL_INTERVAL'))
        
        return overrides

    def apply_cli_overrides(self, cli_options: Dict[str, Any]) -> None:
        """
        Apply command-line interface options as overrides to the configuration.
        
        Args:
            cli_options: Dictionary of CLI options to apply
        """
        if 'theme' in cli_options and cli_options['theme']:
            self.display.theme = cli_options['theme']
        if 'refresh_interval' in cli_options and cli_options['refresh_interval']:
            self.display.refresh_interval = cli_options['refresh_interval']
        if 'log_level' in cli_options and cli_options['log_level']:
            self.logging.level = cli_options['log_level']
        if 'poll_interval' in cli_options and cli_options['poll_interval']:
            self.monitor.poll_interval = cli_options['poll_interval']