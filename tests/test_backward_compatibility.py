"""
Backward compatibility tests for RocotoViewer.

This module contains tests to verify backward compatibility with legacy Rocoto formats.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

from rocotoviewer.parsers.base_parser import BaseParser
from rocotoviewer.parsers.workflow_parser import WorkflowParser
from rocotoviewer.parsers.task_parser import TaskParser
from rocotoviewer.parsers.log_parser import LogParser
from rocotoviewer.utils.compatibility_utils import CompatibilityUtils


class TestBackwardCompatibility:
    """
    Test class for backward compatibility features in RocotoViewer.
    """
    
    def setup_method(self):
        """
        Set up test fixtures before each test method.
        """
        # Create a mock config with proper structure
        self.config = Mock()
        self.config.monitor = Mock()
        self.config.monitor.max_file_size = 10000000  # 10MB
        self.compatibility_utils = CompatibilityUtils()
    
    def test_format_detection_legacy_workflow(self):
        """
        Test format detection for legacy workflow XML.
        """
        # Create a legacy format XML
        legacy_xml = """<?xml version="1.0"?>
        <rocoto workflowid="test_workflow">
            <task name="task1" cycledef="cycle1">
                <command>echo "hello"</command>
            </task>
            <cycledef group="group1">
                <cyclestr>202301010</cyclestr>
            </cycledef>
        </rocoto>
        """
        
        result = self.compatibility_utils.detect_format_version(legacy_xml)
        
        assert result['format'] in ['rocoto_legacy', 'rocoto_v1']
        assert result['confidence'] > 0.0
        assert result['parser_strategy'] in ['legacy', 'v1_compatible']
    
    def test_format_detection_v1_workflow(self):
        """
        Test format detection for version 1 workflow XML.
        """
        # Create a version 1 format XML
        v1_xml = """<?xml version="1.0"?>
        <workflow workflowid="test_workflow">
            <taskdef name="task1" cycledef="cycle1">
                <command>echo "hello"</command>
            </taskdef>
            <cycledef group="group1">
                <cyclestr>2023010100</cyclestr>
            </cycledef>
        </workflow>
        """
        
        result = self.compatibility_utils.detect_format_version(v1_xml)
        
        assert result['format'] == 'rocoto_v1'
        assert result['version'] == '1.x'
        assert result['confidence'] > 0.0
        assert result['parser_strategy'] == 'v1_compatible'
    
    def test_format_detection_v2_workflow(self):
        """
        Test format detection for version 2 workflow XML.
        """
        # Create a version 2 format XML
        v2_xml = """<?xml version="1.0"?>
        <workflow name="test_workflow">
            <tasks>
                <taskdef name="task1">
                    <command>echo "hello"</command>
                </taskdef>
            </tasks>
            <cycledef id="cycle1">
                <start>2023010100</start>
                <end>2023010200</end>
                <interval>06:00:00</interval>
            </cycledef>
        </workflow>
        """
        
        result = self.compatibility_utils.detect_format_version(v2_xml)
        
        assert result['format'] == 'rocoto_v2'
        assert result['version'] == '2.x'
        assert result['confidence'] > 0.0
        assert result['parser_strategy'] == 'v2_compatible'
    
    def test_workflow_parser_legacy_format(self):
        """
        Test workflow parser with legacy format.
        """
        # Create a temporary file with legacy format
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write("""<?xml version="1.0"?>
            <rocoto workflowid="legacy_test">
                <job name="job1" status="S">
                    <command>echo "job1"</command>
                </job>
                <job name="job2" status="F">
                    <command>echo "job2"</command>
                </job>
                <cycledef group="group1">
                    <cyclestr>2023010100</cyclestr>
                </cycledef>
            </rocoto>
            """)
            temp_file = f.name
        
        try:
            parser = WorkflowParser(self.config)
            result = parser.parse(temp_file)
            
            assert result['id'] == 'legacy_test'
            assert len(result['tasks']) == 2
            assert result['format_info']['parser_strategy'] in ['legacy', 'v1_compatible']
            
            # Check that legacy fields were properly mapped
            task_names = [task['id'] for task in result['tasks']]
            assert 'job1' in task_names
            assert 'job2' in task_names
            
            # Check status mapping
            statuses = [task['status'] for task in result['tasks']]
            assert 'SUCCESS' in statuses
            assert 'FAILED' in statuses
            
        finally:
            os.unlink(temp_file)
    
    def test_task_parser_legacy_format(self):
        """
        Test task parser with legacy format.
        """
        # Create a temporary file with legacy format
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write("""<?xml version="1.0"?>
            <tasks>
                <jobdef jobname="legacy_task1" jobid="123" status="S">
                    <command>echo "legacy task"</command>
                </jobdef>
                <taskdef taskname="modern_task2" taskid="456" status="F">
                    <command>echo "modern task"</command>
                </taskdef>
            </tasks>
            """)
            temp_file = f.name
        
        try:
            parser = TaskParser(self.config)
            result = parser.parse(temp_file)
            
            assert result['total_tasks'] >= 1  # At least one task should be parsed
            # Check that format was detected (could be any compatible format)
            assert 'parser_strategy' in result['format_info']
            
            # Check that tasks were parsed (basic validation)
            assert len(result['tasks']) >= 1
            
            # Check that at least one task has some basic attributes
            task = result['tasks'][0]
            assert 'id' in task or 'name' in task
            assert 'status' in task
            
        finally:
            os.unlink(temp_file)
    
    def test_log_parser_legacy_format(self):
        """
        Test log parser with legacy format.
        """
        # Create a temporary file with legacy log format
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("""Jan 01 12:00:00 TASK job1 SUCCESS
Jan 01 12:05:00 TASK job2 FAIL
Jan 01 12:10:00 CYCLE 1 STARTED
Jan 01 12:15:00 NAME job3 STATUS RUN
            """)
            temp_file = f.name
        
        try:
            parser = LogParser(self.config)
            result = parser.parse(temp_file)
            
            # Note: The actual number of lines might include empty lines
            assert result['parsed_lines'] > 0
            # Check that format was detected (could be any compatible format)
            assert 'parser_strategy' in result['format_info']
            
            # Check that log entries were parsed
            assert len(result['logs']) > 0
            
            # Check that at least one log entry has basic attributes
            log = result['logs'][0]
            assert 'timestamp' in log or 'task_id' in log or 'status' in log
            
        finally:
            os.unlink(temp_file)
    
    def test_data_migration_v1_to_v2(self):
        """
        Test data migration from version 1 to version 2.
        """
        v1_data = {
            'workflowid': 'test_workflow',
            'taskdef': [
                {'name': 'task1', 'status': 'S'},
                {'name': 'task2', 'status': 'F'}
            ]
        }
        
        migrated_data = self.compatibility_utils.migrate_data_structure(v1_data, '1.x', '2.x')
        
        # Check that legacy fields were mapped to new fields
        assert 'id' in migrated_data
        assert migrated_data['id'] == 'test_workflow'
        assert 'workflowid' not in migrated_data  # Should be removed
        
        # Check that taskdefs were handled properly
        assert 'taskdef' in migrated_data  # Original structure preserved but could be enhanced
        
        # Generate migration report
        report = self.compatibility_utils.generate_migration_report(v1_data, migrated_data)
        assert 'changes_made' in report
        assert 'summary' in report
    
    def test_legacy_xml_transformation(self):
        """
        Test legacy XML transformation to current format.
        """
        legacy_xml = """<?xml version="1.0"?>
        <rocoto workflowid="legacy_workflow">
            <job jobname="legacy_task" jobid="123" status="S">
                <command>echo "legacy"</command>
            </job>
        </rocoto>
        """
        
        converted_xml = self.compatibility_utils.convert_legacy_xml_to_current(legacy_xml)
        
        # Parse the converted XML to verify structure
        root = ET.fromstring(converted_xml)
        
        # The root should still be 'rocoto' but might have different attributes
        assert root.tag in ['rocoto', 'workflow']
        
        # Find the task/job element
        task_elem = root.find('.//job') or root.find('.//taskdef') or root.find('.//task')
        assert task_elem is not None
        
        # Check that attributes were potentially transformed
        assert 'jobname' in task_elem.attrib or 'name' in task_elem.attrib
    
    def test_compatibility_warnings(self):
        """
        Test generation of compatibility warnings.
        """
        format_info = {
            'version': 'legacy',
            'confidence': 0.3  # Low confidence
        }
        
        warnings = self.compatibility_utils.get_compatibility_warnings(format_info)
        
        # Should have warnings for both low confidence and legacy format
        assert len(warnings) >= 2
        assert any('Low confidence' in w for w in warnings)
        assert any('Legacy format' in w for w in warnings)
    
    def test_legacy_format_validation(self):
        """
        Test validation of legacy format data.
        """
        format_info = {'version': '1.x'}
        
        # Valid data
        valid_data = {'workflowid': 'test', 'id': 'test'}
        assert self.compatibility_utils.validate_legacy_format(valid_data, format_info)
        
        # Invalid data (missing required field in legacy context)
        invalid_data = {}
        assert not self.compatibility_utils.validate_legacy_format(invalid_data, format_info)
    
    def test_base_parser_format_detection(self):
        """
        Test format detection in the base parser.
        """
        # Use the compatibility utils directly for format detection
        result = self.compatibility_utils.detect_format_version("""<rocoto workflowid="test"><job name="task1"/></rocoto>""")
        
        assert result['format'] in ['rocoto_legacy', 'rocoto_v1']
        assert result['confidence'] > 0.0
    
    def test_workflow_parser_backward_compatibility(self):
        """
        Test that workflow parser maintains backward compatibility.
        """
        # Test with a mix of legacy and modern attributes
        xml_content = """<?xml version="1.0"?>
        <workflow workflowid="test" name="modern_test">
            <tasks>
                <taskdef name="task1" status="S"/>
                <jobdef jobname="job1" status="F"/>
            </tasks>
        </workflow>
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_file = f.name
        
        try:
            parser = WorkflowParser(self.config)
            result = parser.parse(temp_file)
            
            # Should handle both legacy and modern formats
            assert result['id'] in ['test', 'modern_test']  # Should map to 'id' field
            assert len(result['tasks']) >= 1 # At least one task should be parsed
            
            # Check that at least one task has basic attributes
            task = result['tasks'][0]
            assert 'id' in task or 'name' in task
            assert 'status' in task
            
        finally:
            os.unlink(temp_file)
    
    def test_error_handling_fallback_parsing(self):
        """
        Test that parsers fall back to alternative parsing methods on error.
        """
        # Create malformed XML that might trigger fallback
        malformed_xml = """<?xml version="1.0"?>
        <workflow workflowid="test">
            <tasks>
                <taskdef name="task1" status="S">
                    <command>echo "test</command>
                </taskdef>
            </tasks>
        </workflow>
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(malformed_xml)
            temp_file = f.name
        
        try:
            # This should handle the error gracefully and potentially use fallback parsing
            parser = WorkflowParser(self.config)
            result = parser.parse(temp_file)
            
            # Should return a valid result even with malformed content
            assert isinstance(result, dict)
            
        finally:
            os.unlink(temp_file)


# Run the tests if this file is executed directly
if __name__ == '__main__':
    pytest.main([__file__])