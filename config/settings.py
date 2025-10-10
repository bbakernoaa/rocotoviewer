"""
Settings management for RocotoViewer.

This module provides application-wide settings and constants.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """Application settings and constants."""
    
    # Application settings
    APP_NAME: str = "RocotoViewer"
    APP_VERSION: str = "0.1.0"
    APP_AUTHOR: str = "RocotoViewer Team"
    
    # Default paths
    DEFAULT_CONFIG_PATH: str = "./rocoto_config.yaml"
    DEFAULT_WORKFLOW_DIR: str = "./workflows"
    DEFAULT_LOG_FILE: str = "./rocotoviewer.log"
    
    # UI settings
    DEFAULT_THEME: str = "default"
    DEFAULT_REFRESH_INTERVAL: int = 5  # seconds
    DEFAULT_MAX_LOG_LINES: int = 1000
    
    # Monitoring settings
    DEFAULT_POLL_INTERVAL: int = 10  # seconds
    DEFAULT_MAX_FILE_SIZE: int = 10485760  # 10MB in bytes
    DEFAULT_MONITOR_ENABLED: bool = True
    
    # Logging settings
    DEFAULT_LOG_LEVEL: str = "INFO"
    
    # File extensions
    WORKFLOW_EXTENSIONS: tuple = ('.xml', '.workflow')
    LOG_EXTENSIONS: tuple = ('.log', '.out', '.err')
    
    # Parsing settings
    MAX_PARSE_RETRIES: int = 3
    PARSE_TIMEOUT: int = 30  # seconds
    
    def __post_init__(self):
        # Ensure extensions are tuples to prevent modification
        if not isinstance(self.WORKFLOW_EXTENSIONS, tuple):
            self.WORKFLOW_EXTENSIONS = tuple(self.WORKFLOW_EXTENSIONS)
        if not isinstance(self.LOG_EXTENSIONS, tuple):
            self.LOG_EXTENSIONS = tuple(self.LOG_EXTENSIONS)