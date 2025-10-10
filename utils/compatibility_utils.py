"""
Compatibility utilities module for RocotoViewer.

This module provides common backward compatibility functions and utilities
for handling different Rocoto format versions.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging
import json
import xml.etree.ElementTree as ET
from datetime import datetime


class CompatibilityUtils:
    """
    Utility class for backward compatibility operations in RocotoViewer.
    """
    
    def __init__(self):
        """
        Initialize compatibility utilities.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Format detection patterns for different Rocoto versions
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
        
        # Field mapping for legacy to current format conversion
        self.field_mappings = {
            # Workflow mappings
            'workflowid': 'id',
            'jobname': 'name',
            'jobid': 'id',
            'taskdef': 'task',
            'cycledef_group': 'cycledef',
            
            # Task mappings
            'taskname': 'name',
            'taskid': 'id',
            'jobdef': 'task',
            
            # Status mappings
            'S': 'SUCCESS',
            'F': 'FAILED',
            'R': 'RUNNING',
            'Q': 'QUEUED',
            'H': 'HELD',
            'U': 'UNKNOWN',
            'succeeded': 'SUCCESS',
            'failed': 'FAILED',
            'running': 'RUNNING',
            'queued': 'QUEUED',
            'held': 'HELD',
            'unknown': 'UNKNOWN'
        }
    
    def detect_format_version(self, source: Union[str, Path]) -> Dict[str, Any]:
        """
        Detect the format version of a source file for backward compatibility.
        
        Args:
            source: Source file path or content string
            
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
        if isinstance(source, (str, Path)):
            path = Path(source)
            if path.exists():
                try:
                    with open(path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                except Exception as e:
                    self.logger.error(f"Error reading file {source}: {str(e)}")
                    return result
            else:
                # Assume it's content string
                content = str(source)
        
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
        
        migrated_data = self._deep_copy_dict(data)
        
        # Example migration: rename deprecated fields
        if from_version.startswith('1.') and to_version.startswith('2.'):
            # Migrate workflow fields
            if 'workflowid' in migrated_data and 'id' not in migrated_data:
                migrated_data['id'] = migrated_data.pop('workflowid')
            
            # Migrate task fields
            if 'tasks' in migrated_data:
                migrated_data['tasks'] = [
                    self._migrate_task_fields(task, from_version, to_version)
                    for task in migrated_data['tasks']
                ]
        
        # Add more migration rules as needed
        return migrated_data
    
    def _migrate_task_fields(self, task: Dict[str, Any], from_version: str, to_version: str) -> Dict[str, Any]:
        """
        Migrate individual task fields from one version to another.
        
        Args:
            task: Task data to migrate
            from_version: Source version
            to_version: Target version
            
        Returns:
            Migrated task data
        """
        migrated_task = self._deep_copy_dict(task)
        
        # Apply field mappings
        for old_field, new_field in self.field_mappings.items():
            if old_field in migrated_task and new_field not in migrated_task:
                migrated_task[new_field] = migrated_task.pop(old_field)
        
        return migrated_task
    
    def _deep_copy_dict(self, data: Any) -> Any:
        """
        Create a deep copy of a dictionary structure.
        
        Args:
            data: Data to copy
            
        Returns:
            Deep copy of the data
        """
        if isinstance(data, dict):
            return {key: self._deep_copy_dict(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._deep_copy_dict(item) for item in data]
        else:
            return data
    
    def handle_legacy_format(self, data: Dict[str, Any], format_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle legacy format data and convert to current format.
        
        Args:
            data: Legacy format data
            format_info: Format detection information
            
        Returns:
            Converted data in current format
        """
        converted_data = self._deep_copy_dict(data)
        
        # Handle legacy field names and structures
        if format_info.get('version', 'unknown') == 'legacy':
            # Apply field mappings
            for old_field, new_field in self.field_mappings.items():
                if old_field in converted_data and new_field not in converted_data:
                    converted_data[new_field] = converted_data.pop(old_field)
        
        # Handle version 1.x formats
        if format_info.get('version', '').startswith('1.'):
            # Apply version-specific transformations
            if 'workflowid' in converted_data:
                converted_data['id'] = converted_data.pop('workflowid')
        
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
        
        if format_info.get('version', 'unknown').startswith('1.'):
            warnings.append("Rocoto version 1.x detected. Some newer features may not be available.")
        
        return warnings
    
    def validate_legacy_format(self, data: Dict[str, Any], format_info: Dict[str, Any]) -> bool:
        """
        Validate data against legacy format expectations.
        
        Args:
            data: Data to validate
            format_info: Format detection information
            
        Returns:
            True if data is valid for the format, False otherwise
        """
        if not data:
            return False
        
        # Check for format-specific requirements
        if format_info.get('version', '').startswith('1.'):
            # Version 1.x might have specific requirements
            required_fields = ['id']  # Example for workflow
            for field in required_fields:
                if field not in data and f'workflow{field}' not in data:
                    self.logger.warning(f"Missing field {field} for version {format_info['version']}")
                    return False
        
        return True
    
    def convert_legacy_xml_to_current(self, xml_content: str) -> str:
        """
        Convert legacy XML format to current format.
        
        Args:
            xml_content: Legacy XML content
            
        Returns:
            Converted XML content in current format
        """
        try:
            root = ET.fromstring(xml_content)
            
            # Apply transformations based on detected format
            self._transform_legacy_xml(root)
            
            return ET.tostring(root, encoding='unicode')
        except ET.ParseError as e:
            self.logger.error(f"Error parsing XML: {str(e)}")
            return xml_content  # Return original if transformation fails
    
    def _transform_legacy_xml(self, root: ET.Element):
        """
        Apply transformations to convert legacy XML structure to current format.
        
        Args:
            root: Root XML element to transform
        """
        # Transform root element attributes
        for old_attr, new_attr in self.field_mappings.items():
            if old_attr in root.attrib and new_attr not in root.attrib:
                root.attrib[new_attr] = root.attrib.pop(old_attr)
        
        # Transform child elements
        for child in root:
            self._transform_element(child)
    
    def _transform_element(self, element: ET.Element):
        """
        Transform an individual XML element for legacy compatibility.
        
        Args:
            element: XML element to transform
        """
        # Transform element attributes
        for old_attr, new_attr in self.field_mappings.items():
            if old_attr in element.attrib and new_attr not in element.attrib:
                element.attrib[new_attr] = element.attrib.pop(old_attr)
        
        # Transform child elements recursively
        for child in element:
            self._transform_element(child)
    
    def generate_migration_report(self, original_data: Dict[str, Any], migrated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a report of changes made during migration.
        
        Args:
            original_data: Original data before migration
            migrated_data: Data after migration
            
        Returns:
            Migration report with changes
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'changes_made': [],
            'warnings': [],
            'summary': {
                'original_size': len(json.dumps(original_data)) if original_data else 0,
                'migrated_size': len(json.dumps(migrated_data)) if migrated_data else 0,
                'format_changed': original_data != migrated_data
            }
        }
        
        # Compare and record changes
        self._compare_data(original_data, migrated_data, report['changes_made'], '')
        
        return report
    
    def _compare_data(self, original: Any, migrated: Any, changes: List[Dict[str, Any]], path: str):
        """
        Compare original and migrated data to identify changes.
        
        Args:
            original: Original data
            migrated: Migrated data
            changes: List to store changes
            path: Current path in the data structure
        """
        if isinstance(original, dict) and isinstance(migrated, dict):
            for key in set(original.keys()) | set(migrated.keys()):
                current_path = f"{path}.{key}" if path else key
                if key not in original:
                    changes.append({
                        'type': 'added',
                        'path': current_path,
                        'value': migrated[key]
                    })
                elif key not in migrated:
                    changes.append({
                        'type': 'removed',
                        'path': current_path,
                        'value': original[key]
                    })
                elif original[key] != migrated[key]:
                    changes.append({
                        'type': 'modified',
                        'path': current_path,
                        'original_value': original[key],
                        'new_value': migrated[key]
                    })
                    # Recursively compare nested structures
                    if isinstance(original[key], (dict, list)) and isinstance(migrated[key], (dict, list)):
                        self._compare_data(original[key], migrated[key], changes, current_path)
        elif isinstance(original, list) and isinstance(migrated, list):
            max_len = max(len(original), len(migrated))
            for i in range(max_len):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                if i >= len(original):
                    changes.append({
                        'type': 'added',
                        'path': current_path,
                        'value': migrated[i]
                    })
                elif i >= len(migrated):
                    changes.append({
                        'type': 'removed',
                        'path': current_path,
                        'value': original[i]
                    })
                elif original[i] != migrated[i]:
                    changes.append({
                        'type': 'modified',
                        'path': current_path,
                        'original_value': original[i],
                        'new_value': migrated[i]
                    })
                    # Recursively compare nested structures
                    if isinstance(original[i], (dict, list)) and isinstance(migrated[i], (dict, list)):
                        self._compare_data(original[i], migrated[i], changes, current_path)