"""
Default theme module for RocotoViewer Textual UI.

This module defines the default theme for the application UI.
"""

from typing import Dict, Any
import logging

from textual.theme import Theme


class DefaultTheme(Theme):
    """
    Default theme for RocotoViewer UI.
    """
    
    def __init__(self):
        """
        Initialize the default theme.
        """
        super().__init__(
            name="rocotoviewer-default",
            primary="#007BFF",
            secondary="#6C757D",
            warning="#FFC107",
            error="#DC3545",
            success="#28A745",
            accent="#17A2B8",
            dark=True,
            background="#1E1E1E",
            surface="#2D2D2D",
            panel="#3E3E3E",
            border="#555555",
            text="#FFFFFF",
        )
        
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Additional custom styles for RocotoViewer
        self.styles = {
            # Custom styles for workflow viewer
            ".workflow-viewer-container": {
                "height": "100%",
            },
            ".task-table": {
                "height": "1fr",
            },
            ".workflow-details": {
                "height": "20",
                "border": "round #555555",
                "padding": (1, 1),
            },
            
            # Custom styles for log viewer
            ".log-viewer-container": {
                "height": "100%",
            },
            ".log-table": {
                "height": "1fr",
            },
            ".log-details": {
                "height": "15",
                "border": "round #55555",
                "padding": (1, 1),
            },
            
            # Custom styles for navigation
            ".nav-title": {
                "text-style": "bold",
                "content-align": "center",
                "background": "#333333",
                "color": "#007BFF",
            },
            ".nav-item": {
                "margin": (1, 0),
                "padding": (0, 1),
            },
            
            # Custom styles for search filter
            ".search-filter-container": {
                "border": "solid #555555",
                "padding": (1, 1),
            },
            ".filter-label": {
                "width": "15",
                "text-style": "bold",
            },
            
            # Custom styles for screen titles
            ".screen-title": {
                "text-style": "bold",
                "content-align": "center",
                "background": "#33333",
                "color": "#007BFF",
                "margin": (0, 0, 1, 0),
            },
            
            # Custom styles for section titles
            ".section-title": {
                "text-style": "bold",
                "color": "#007BFF",
                "margin": (1, 0),
            },
            
            # Custom styles for main containers
            "#main-screen-container": {
                "layout": "horizontal",
                "height": "100%",
            },
            "#log-viewer-container": {
                "layout": "horizontal",
                "height": "100%",
            },
            "#workflow-viewer-container": {
                "layout": "horizontal",
                "height": "1fr",
            },
        }
    
    def get_color(self, color_name: str) -> str:
        """
        Get a color by name.
        
        Args:
            color_name: Name of the color to retrieve
            
        Returns:
            Color string
        """
        color_map = {
            'primary': self.primary,
            'secondary': self.secondary,
            'warning': self.warning,
            'error': self.error,
            'success': self.success,
            'accent': self.accent,
            'background': self.background,
            'text': self.text,
            'border': self.border,
        }
        
        if color_name not in color_map:
            self.logger.warning(f"Color '{color_name}' not found in theme, using default")
            return '#FFFFFF'  # Default to white
        
        return color_map[color_name]
    
    def get_status_color(self, status: str) -> str:
        """
        Get an appropriate color for a status string.
        
        Args:
            status: Status string (e.g., 'success', 'error', 'running', etc.)
            
        Returns:
            Color string for the status
        """
        status_lower = status.lower()
        
        if any(s in status_lower for s in ['success', 'succeeded', 'ok', 'active', 'running']):
            return self.success
        elif any(s in status_lower for s in ['error', 'failed', 'failure', 'critical']):
            return self.error
        elif any(s in status_lower for s in ['warning', 'warn', 'pending', 'waiting']):
            return self.warning
        elif any(s in status_lower for s in ['info', 'debug', 'verbose']):
            return self.primary
        else:
            return self.text
    
    def get_workflow_status_style(self, status: str) -> str:
        """
        Get Textual-style formatting for a workflow status.
        
        Args:
            status: Workflow status string
            
        Returns:
            Textual-style formatting string
        """
        color = self.get_status_color(status)
        return f"bold {color} on #33333"
    
    def get_task_status_style(self, status: str) -> str:
        """
        Get Textual-style formatting for a task status.
        
        Args:
            status: Task status string
            
        Returns:
            Textual-style formatting string
        """
        color = self.get_status_color(status)
        return f"bold {color}"
    
    def get_log_level_style(self, level: str) -> str:
        """
        Get Textual-style formatting for a log level.
        
        Args:
            level: Log level string
            
        Returns:
            Textual-style formatting string
        """
        level_lower = level.lower()
        
        if level_lower == 'error':
            return f"bold {self.error}"
        elif level_lower == 'warning':
            return f"bold {self.warning}"
        elif level_lower == 'info':
            return f"bold {self.primary}"
        elif level_lower == 'debug':
            return f"bold {self.accent}"
        else:
            return f"{self.text}"
    
    @classmethod
    def get_theme_config(cls) -> Dict[str, Any]:
        """
        Get the complete theme configuration.
        
        Returns:
            Complete theme configuration dictionary
        """
        theme = cls()
        return {
            'name': theme.name,
            'primary': theme.primary,
            'secondary': theme.secondary,
            'warning': theme.warning,
            'error': theme.error,
            'success': theme.success,
            'accent': theme.accent,
            'dark': theme.dark,
            'background': theme.background,
            'surface': theme.surface,
            'panel': theme.panel,
            'border': theme.border,
            'text': theme.text,
        }
    
    def apply_to_app(self, app) -> None:
        """
        Apply theme settings to a Textual app.
        
        Args:
            app: Textual app instance to apply theme to
        """
        # In a real implementation, this would apply the theme
        # to the app's style system
        pass