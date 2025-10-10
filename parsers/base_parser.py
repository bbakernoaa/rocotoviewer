"""
Base parser module for RocotoViewer.

This module provides a base class for all parsers with common functionality
and backward compatibility features.
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod
import logging
import json
from datetime import datetime


class BaseParser(ABC):
    """
    Abstract base class for all parsers in RocotoViewer with backward compatibility support.
    """
    
    def __init__(self, config=None):
        """
        Initialize the base parser.
        
        Args:
            config: Application configuration (optional)
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Format detection patterns for backward compatibility
        self.format_detection_patterns = {
            'rocoto_v1': [
                r'<workflow[^>]*workflowid',
                r'<task[^>]*cycledef',
                r'<cycledef[^>]*group',
            ],
            'rocoto_v2': [
                r'<workflow[^>]*name',
                r'<taskdef[^>]*name',
                r'<cycledef[^>]*id',
            ],
            'rocoto_legacy': [
                r'<rocoto',
                r'<job',
                r'<dependency[^>]*task',
            ],
            'log_format_v1': [
                r'task.*succeeded',
                r'task.*failed',
                r'cycle.*\d+',
            ],
            'log_format_v2': [
                r'R\d{4}',
                r'CYCLE.*\d+',
                r'TASK.*\w+',
            ]
        }
    
    @abstractmethod
    def parse(self, source: str) -> Dict[str, Any]:
        """
        Parse the source and return structured data.
        
        Args:
            source: Source to parse (file path, string, etc.)
            
        Returns:
            Dictionary with parsed data
        """
        pass
    
    def detect_format_version(self, source: str) -> Dict[str, Any]:
        """
        Detect the format version of the source file for backward compatibility.
        
        Args:
            source: Source to analyze
            
        Returns:
            Dictionary with format detection results
        """
        result = {
            'format': 'unknown',
            'version': 'unknown',
            'confidence': 0.0,
            'parser_strategy': 'default',
            'compatibility_notes': []
        }
        
        # Read content for analysis
        content = None
        if self._is_file_path(source):
            if self.validate_source(source):
                content = self.read_file(source)
        else:
            content = source
        
        if not content:
            return result
        
        # Analyze content to detect format
        detected_formats = []
        
        for format_name, patterns in self.format_detection_patterns.items():
            match_count = 0
            total_patterns = len(patterns)
            
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    match_count += 1
            
            if match_count > 0:
                confidence = match_count / total_patterns
                detected_formats.append((format_name, confidence))
        
        # Sort by confidence
        detected_formats.sort(key=lambda x: x[1], reverse=True)
        
        if detected_formats:
            best_match = detected_formats[0]
            result['format'] = best_match[0]
            result['confidence'] = best_match[1]
            
            # Set version based on format
            if 'v1' in best_match[0]:
                result['version'] = '1.x'
            elif 'v2' in best_match[0]:
                result['version'] = '2.x'
            elif 'legacy' in best_match[0]:
                result['version'] = 'legacy'
            
            # Set parser strategy
            if 'legacy' in best_match[0]:
                result['parser_strategy'] = 'legacy'
            elif 'v1' in best_match[0]:
                result['parser_strategy'] = 'v1_compatible'
            elif 'v2' in best_match[0]:
                result['parser_strategy'] = 'v2_compatible'
            else:
                result['parser_strategy'] = 'default'
        
        return result
    
    def _is_file_path(self, source: str) -> bool:
        """
        Check if source is a file path or content string.
        
        Args:
            source: String to check
            
        Returns:
            True if it's likely a file path, False if content
        """
        # Check if source is a valid file path
        path = Path(source)
        return path.exists() or ('/' in source or '\\' in source)
    
    def validate_source(self, source: str) -> bool:
        """
        Validate that the source exists and is accessible.
        
        Args:
            source: Source path to validate
            
        Returns:
            True if source is valid, False otherwise
        """
        path = Path(source)
        if not path.exists():
            self.logger.error(f"Source does not exist: {source}")
            return False
        
        if path.is_dir():
            self.logger.error(f"Source is a directory, expected a file: {source}")
            return False
        
        # Check file size against max allowed
        if self.config and hasattr(self.config, 'monitor') and hasattr(self.config.monitor, 'max_file_size'):
            max_size = self.config.monitor.max_file_size
            if path.stat().st_size > max_size:
                self.logger.error(f"Source file too large: {source} ({path.stat().st_size} bytes, max: {max_size})")
                return False
        
        return True
    
    def read_file(self, file_path: str, encoding: str = 'utf-8') -> Optional[str]:
        """
        Safely read a file with proper error handling.
        
        Args:
            file_path: Path to the file to read
            encoding: File encoding (default: utf-8)
            
        Returns:
            File content as string or None if error occurred
        """
        try:
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {str(e)}")
            return None
    
    def safe_parse_int(self, value: Any, default: int = 0) -> int:
        """
        Safely parse a value to integer.
        
        Args:
            value: Value to parse
            default: Default value if parsing fails
            
        Returns:
            Parsed integer or default value
        """
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def safe_parse_float(self, value: Any, default: float = 0.0) -> float:
        """
        Safely parse a value to float.
        
        Args:
            value: Value to parse
            default: Default value if parsing fails
            
        Returns:
            Parsed float or default value
        """
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def safe_get_dict_value(self, data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """
        Safely get a value from a dictionary.
        
        Args:
            data: Dictionary to get value from
            key: Key to retrieve
            default: Default value if key doesn't exist
            
        Returns:
            Value from dictionary or default
        """
        try:
            return data.get(key, default)
        except AttributeError:
            return default
    
    def migrate_data_structure(self, data: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
        """
        Migrate data structure from one version to another for backward compatibility.
        
        Args:
            data: Data to migrate
            from_version: Source version
            to_version: Target version
            
        Returns:
            Migrated data structure
        """
        if from_version == to_version:
            return data
        
        migrated_data = data.copy()
        
        # Example migration: rename deprecated fields
        if from_version.startswith('1.') and to_version.startswith('2.'):
            # Example migration from v1 to v2
            if 'workflowid' in migrated_data and 'id' not in migrated_data:
                migrated_data['id'] = migrated_data.pop('workflowid')
            
            if 'taskdef' in migrated_data and 'tasks' not in migrated_data:
                migrated_data['tasks'] = migrated_data.pop('taskdef')
        
        # Add more migration rules as needed
        return migrated_data
    
    def handle_legacy_format(self, data: Dict[str, Any], format_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle legacy format data and convert to current format.
        
        Args:
            data: Legacy format data
            format_info: Format detection information
            
        Returns:
            Converted data in current format
        """
        converted_data = data.copy()
        
        # Handle legacy field names and structures
        if format_info.get('version', '').startswith('1.'):
            # Example legacy handling
            if 'workflowid' in converted_data:
                converted_data['id'] = converted_data.pop('workflowid')
        
        # Add more legacy handling as needed
        return converted_data
    
    def get_compatibility_warnings(self, format_info: Dict[str, Any]) -> List[str]:
        """
        Get compatibility warnings for the detected format.
        
        Args:
            format_info: Format detection information
            
        Returns:
            List of compatibility warnings
        """
        warnings = []
        
        if format_info.get('confidence', 0) < 0.5:
            warnings.append("Low confidence in format detection. Manual verification recommended.")
        
        if format_info.get('version', 'unknown') == 'legacy':
            warnings.append("Legacy format detected. Some features may not be fully supported.")
        
        return warnings