from typing import Dict, Optional, Union
from pathlib import Path
import json
from dlens.resources.resources_manager import ResourcesManager

class ThemeManager:
    """Manages themes for directory visualization"""
    
    def __init__(self, theme_name: Optional[str] = None, theme_path: Optional[Union[str, Path]] = None):
        """
        Initialize theme manager with optional theme name and custom theme path
        
        Args:
            theme_name: Name of the theme to use (default: 'default')
            theme_path: Optional path to custom themes file
        """
        self._themes_data = self._load_themes(theme_path)
        self._current_theme = self._get_theme(theme_name or 'default')
        
    def _load_themes(self, theme_path: Optional[Union[str, Path]] = None) -> Dict:
        """Load themes from file"""
        try:
            # Load themes from custom path if provided
            if theme_path:
                with open(theme_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            # Otherwise load from package resources
            return ResourcesManager.get_themes()
            
        except Exception as e:
            print(f"Warning: Error loading themes ({str(e)}), using fallback theme")
            # Fallback theme data if loading fails
            return {
                "themes": [{
                    "name": "default",
                    "description": "Fallback theme",
                    "colors": {
                        "directory": "bold light_green",
                        "file": "bold yellow",
                        "root": "bold red",
                        "details": "dim cyan",
                        "more_items": "dim",
                        "subdirectory_count": "dim"
                    }
                }]
            }

    def _get_theme(self, theme_name: str) -> Dict:
        """
        Get theme by name
        
        Args:
            theme_name: Name of the theme to retrieve
            
        Returns:
            Dict containing theme colors, falling back to default if not found
        """
        # Find the requested theme in themes list
        theme = next(
            (theme for theme in self._themes_data["themes"] 
             if theme["name"].lower() == theme_name.lower()),
            None
        )
        
        if not theme:
            # If theme not found, use default
            theme = next(
                theme for theme in self._themes_data["themes"]
                if theme["name"] == "default"
            )
        
        # Extract and return just the colors with theme metadata
        return {
            "name": theme["name"],
            "description": theme["description"],
            **theme["colors"]
        }

    @property
    def theme(self) -> Dict:
        """Get current theme configuration"""
        return self._current_theme
    
    @property
    def available_themes(self) -> list:
        """Get list of available theme names"""
        return [theme["name"] for theme in self._themes_data["themes"]]
    
    def set_theme(self, theme_name: str) -> None:
        """
        Change current theme
        
        Args:
            theme_name: Name of theme to switch to
        """
        self._current_theme = self._get_theme(theme_name)

    def get_color(self, element: str, fallback: Optional[str] = None) -> str:
        """
        Get color style for a specific element
        
        Args:
            element: Element type to get color for (directory, file, etc)
            fallback: Fallback style if element not found in theme
            
        Returns:
            Style string for the element
        """
        return self._current_theme.get(element, fallback or "")