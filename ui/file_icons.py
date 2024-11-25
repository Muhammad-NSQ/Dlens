from pathlib import Path
from dlens.resources.resources_manager import ResourcesManager
from typing import Union


class FileTypeIcons:
    """Manage file type icons for enhanced visualization"""
    
    _icons = None  # Store loaded icons data
    
    @classmethod
    def load_icons(cls, json_path: Union[str, Path] = None):
        """Load icons from JSON file, but only once."""
        if cls._icons is not None:
            # Icons are already loaded, no need to reload
            return
        
        # Get icons data using the centralized ResourcesManager
        icons_data = ResourcesManager.get_icons(json_path)
        
        # Combine both dictionaries for internal usage
        cls._icons = {
            **icons_data['file_types'],
            **icons_data['special']
        }
    
    @classmethod
    def get_icon(cls, path: Path) -> str:
        """Get appropriate icon for file type"""
        if cls._icons is None:
            cls.load_icons()  # Load icons once if they haven't been loaded yet
            
        if path.is_dir():
            return cls._icons['directory']
        if path.is_symlink():
            return cls._icons['symlink']
        return cls._icons.get(path.suffix.lower(), cls._icons['default'])
