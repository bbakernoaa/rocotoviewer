"""
Event bus module for RocotoViewer.

This module provides a centralized event system for communication
between different parts of the application.
"""

import threading
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass
from datetime import datetime
import logging


@dataclass
class Event:
    """
    Base event class for the event bus system.
    """
    type: str
    data: Any = None
    timestamp: datetime = None
    source: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class EventBus:
    """
    Centralized event bus for application communication.
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self._handlers: Dict[str, List[Callable]] = {}
        self._type_handlers: Dict[Type, List[Callable]] = {}
        self._lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
    
    def subscribe(self, event_type: str, handler: Callable):
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            handler: Function to call when event is published
        """
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            self._handlers[event_type].append(handler)
            self.logger.debug(f"Subscribed to event type: {event_type}")
    
    def subscribe_to_type(self, event_class: Type, handler: Callable):
        """
        Subscribe to a specific event class type.
        
        Args:
            event_class: Event class to subscribe to
            handler: Function to call when event is published
        """
        with self._lock:
            if event_class not in self._type_handlers:
                self._type_handlers[event_class] = []
            self._type_handlers[event_class].append(handler)
            self.logger.debug(f"Subscribed to event type: {event_class.__name__}")
    
    def unsubscribe(self, event_type: str, handler: Callable):
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove
        """
        with self._lock:
            if event_type in self._handlers:
                try:
                    self._handlers[event_type].remove(handler)
                    self.logger.debug(f"Unsubscribed from event type: {event_type}")
                except ValueError:
                    pass # Handler was not subscribed
    
    def publish(self, event: Union[Event, str], data: Any = None, source: str = None):
        """
        Publish an event to all subscribed handlers.
        
        Args:
            event: Event object or event type string
            data: Data to include with the event (if event is a string)
            source: Source identifier for the event
        """
        if isinstance(event, str):
            event = Event(type=event, data=data, source=source)
        
        self.logger.debug(f"Publishing event: {event.type} from {event.source or 'unknown'}")
        
        # Call handlers for the specific event type
        with self._lock:
            handlers = self._handlers.get(event.type, [])
            type_handlers = []
            
            # Find handlers for parent types too
            for event_class, class_handlers in self._type_handlers.items():
                if isinstance(event, event_class):
                    type_handlers.extend(class_handlers)
        
        # Execute handlers (outside the lock to prevent deadlocks)
        all_handlers = handlers + type_handlers
        for handler in all_handlers:
            try:
                handler(event)
            except Exception as e:
                self.logger.error(f"Error in event handler for {event.type}: {str(e)}")
    
    def clear_subscribers(self, event_type: str = None):
        """
        Clear subscribers for a specific event type or all types.
        
        Args:
            event_type: Event type to clear, or None to clear all
        """
        with self._lock:
            if event_type:
                if event_type in self._handlers:
                    del self._handlers[event_type]
                self.logger.debug(f"Cleared subscribers for event type: {event_type}")
            else:
                self._handlers.clear()
                self._type_handlers.clear()
                self.logger.debug("Cleared all subscribers")


# Predefined event types for common application events
class WorkflowEvent(Event):
    """Event related to workflow changes."""
    pass


class UIEvent(Event):
    """Event related to UI changes."""
    pass


class LogEvent(Event):
    """Event related to log processing."""
    pass


class FileEvent(Event):
    """Event related to file system changes."""
    pass


# Global event bus instance
_global_event_bus: Optional[EventBus] = None
_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """
    Get the global event bus instance.
    
    Returns:
        Global event bus instance
    """
    global _global_event_bus
    
    with _bus_lock:
        if _global_event_bus is None:
            _global_event_bus = EventBus()
    
    return _global_event_bus


def publish_event(event: Union[Event, str], data: Any = None, source: str = None):
    """
    Publish an event using the global event bus.
    
    Args:
        event: Event object or event type string
        data: Data to include with the event
        source: Source identifier for the event
    """
    bus = get_event_bus()
    bus.publish(event, data, source)


def subscribe_to_event(event_type: str, handler: Callable):
    """
    Subscribe to an event using the global event bus.
    
    Args:
        event_type: Type of event to subscribe to
        handler: Function to call when event is published
    """
    bus = get_event_bus()
    bus.subscribe(event_type, handler)