"""
Integration tests for RocotoViewer components.

This module tests the integration between different components of the RocotoViewer,
including event bus communication, state management, and UI updates.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from ..core.event_bus import EventBus, WorkflowEvent
from ..core.state_manager import StateManager
from ..parsers.workflow_parser import WorkflowParser
from ..ui.widgets.workflow_viewer import WorkflowViewer
from ..config.config import Config


class TestIntegration:
    """Integration tests for RocotoViewer components."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock(spec=Config)
        config.display = Mock()
        config.display.theme = "default"
        config.display.refresh_interval = 5
        return config
    
    @pytest.fixture
    def event_bus(self):
        """Create an event bus instance."""
        return EventBus()
    
    @pytest.fixture
    def state_manager(self, mock_config):
        """Create a state manager instance."""
        return StateManager(mock_config)
    
    @pytest.fixture
    def workflow_parser(self):
        """Create a workflow parser instance."""
        return WorkflowParser()
    
    def test_event_bus_integration(self, event_bus, state_manager):
        """Test integration between event bus and state manager."""
        # Register a callback to track events
        events_received = []
        
        def event_callback(event):
            events_received.append(event)
        
        event_bus.subscribe("test_event", event_callback)
        
        # Publish an event
        test_data = {"workflow_id": "test_wf", "status": "running"}
        event_bus.publish("test_event", test_data, "test_source")
        
        # Verify the event was received
        assert len(events_received) == 1
        assert events_received[0].type == "test_event"
        assert events_received[0].data == test_data
        assert events_received[0].source == "test_source"
    
    def test_workflow_event_propagation(self, event_bus, state_manager):
        """Test workflow event propagation through the system."""
        # Register state manager to handle workflow events
        events_handled = []
        
        def workflow_handler(event):
            events_handled.append(event)
            if event.type == "workflow_updated":
                # Simulate updating workflow in state
                workflow_data = event.data.get("workflow_data", {})
                state_manager.update_workflow(event.data["workflow_id"], workflow_data)
        
        event_bus.subscribe_to_type(WorkflowEvent, workflow_handler)
        
        # Publish a workflow event
        workflow_data = {
            "workflow_id": "test_workflow",
            "workflow_data": {
                "id": "test_workflow",
                "name": "Test Workflow",
                "tasks": [
                    {"id": "task1", "status": "success"},
                    {"id": "task2", "status": "running"}
                ]
            }
        }
        
        event_bus.publish(WorkflowEvent(
            type="workflow_updated",
            data=workflow_data,
            source="test"
        ))
        
        # Verify the event was handled and state was updated
        assert len(events_handled) == 1
        stored_workflow = state_manager.get_workflow("test_workflow")
        assert stored_workflow is not None
        assert stored_workflow["data"]["id"] == "test_workflow"
        assert len(stored_workflow["data"]["tasks"]) == 2
    
    @patch('textual.app.App.run')
    def test_workflow_viewer_updates_on_state_change(self, mock_run, mock_config, state_manager, workflow_parser):
        """Test that workflow viewer updates when state changes."""
        # Create a mock log processor
        log_processor = Mock()
        
        # Create workflow viewer
        viewer = WorkflowViewer(mock_config, state_manager, log_processor, workflow_parser)
        
        # Add a workflow to state
        workflow_data = {
            "id": "test_workflow",
            "name": "Test Workflow",
            "tasks": [
                {"id": "task1", "status": "success", "cycle": "2023010100"},
                {"id": "task2", "status": "running", "cycle": "2023010106"}
            ]
        }
        
        state_manager.update_workflow("test_workflow", workflow_data)
        
        # Verify workflow appears in viewer's workflows list
        viewer.update_workflows()
        assert len(viewer.workflows) == 1
        assert viewer.workflows[0]["id"] == "test_workflow"
        assert viewer.workflows[0]["name"] == "Test Workflow"
    
    def test_component_communication_chain(self, event_bus, state_manager):
        """Test the complete communication chain from event to state to UI."""
        # Track events at each stage
        events_received = []
        state_updates = []
        
        # Event bus handler
        def event_handler(event):
            events_received.append(event)
            # Simulate processing and updating state
            if event.type == "workflow_state_changed":
                workflow_id = event.data["workflow_id"]
                workflow_data = event.data.get("workflow_data", {})
                state_manager.update_workflow(workflow_id, workflow_data)
                state_updates.append((workflow_id, workflow_data))
        
        event_bus.subscribe_to_type(WorkflowEvent, event_handler)
        
        # Simulate a workflow state change event
        workflow_data = {
            "workflow_id": "integration_test_wf",
            "workflow_data": {
                "id": "integration_test_wf",
                "name": "Integration Test Workflow",
                "tasks": [
                    {"id": "int_task1", "status": "queued"},
                    {"id": "int_task2", "status": "success"}
                ],
                "status": "active"
            }
        }
        
        event = WorkflowEvent(
            type="workflow_state_changed",
            data=workflow_data,
            source="integration_test"
        )
        
        event_bus.publish(event)
        
        # Verify the complete chain worked
        assert len(events_received) == 1
        assert len(state_updates) == 1
        assert state_updates[0][0] == "integration_test_wf"
        
        # Verify state was actually updated
        stored_workflow = state_manager.get_workflow("integration_test_wf")
        assert stored_workflow is not None
        assert stored_workflow["data"]["status"] == "active"
        assert len(stored_workflow["data"]["tasks"]) == 2
    
    @pytest.mark.asyncio
    async def test_async_event_handling(self, event_bus, state_manager):
        """Test asynchronous event handling."""
        # Track async events
        async_events = []
        
        async def async_handler(event):
            async_events.append(event)
            # Simulate async processing
            await asyncio.sleep(0.01)
            # Update state after async processing
            if event.type == "async_workflow_update":
                workflow_data = event.data.get("workflow_data", {})
                state_manager.update_workflow(event.data["workflow_id"], workflow_data)
        
        event_bus.subscribe_to_type(WorkflowEvent, async_handler)
        
        # Publish async event
        workflow_data = {
            "workflow_id": "async_test_wf",
            "workflow_data": {
                "id": "async_test_wf",
                "name": "Async Test Workflow",
                "tasks": [{"id": "async_task1", "status": "running"}]
            }
        }
        
        event = WorkflowEvent(
            type="async_workflow_update",
            data=workflow_data,
            source="async_test"
        )
        
        # In a real scenario, we'd await this, but for testing we'll simulate
        # the event loop processing
        event_bus.publish(event)
        
        # Give the event loop a chance to process
        await asyncio.sleep(0.02)
        
        # Verify async processing occurred
        # Note: In a real test, we'd have more sophisticated verification
        stored_workflow = state_manager.get_workflow("async_test_wf")
        assert stored_workflow is not None


# Additional integration tests can be added here as needed