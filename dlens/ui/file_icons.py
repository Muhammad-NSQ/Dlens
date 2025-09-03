import threading
import logging
from pathlib import Path
from dlens.resources.resources_manager import ResourcesManager
from typing import Union, Dict


class FileTypeIcons:
    """Manage file type icons for enhanced visualization with thread safety"""
    
    _icons = None  # Store loaded icons data
    _lock = threading.Lock()  # Thread safety for icon loading
    
    @classmethod
    def load_icons(cls, json_path: Union[str, Path] = None):
        """Load icons from JSON file, but only once with thread safety."""
        with cls._lock:
            if cls._icons is not None:
                # Icons are already loaded, no need to reload
                return
            
            try:
                # Get icons data using the centralized ResourcesManager
                icons_data = ResourcesManager.get_icons(json_path)
                
                # Validate icons data structure
                if not isinstance(icons_data, dict):
                    raise ValueError("Icons data must be a dictionary")
                
                if 'file_types' not in icons_data or 'special' not in icons_data:
                    raise ValueError("Icons data must contain 'file_types' and 'special' keys")
                
                # Combine both dictionaries for internal usage
                cls._icons = {
                    **icons_data['file_types'],
                    **icons_data['special']
                }
                
                logging.info(f"Loaded {len(cls._icons)} file type icons")
                
            except Exception as e:
                logging.error(f"Failed to load icons: {e}")
                # Fallback to minimal icons if loading fails
                cls._icons = {
                    'default': '📄',
                    'directory': '📁',
                    'symlink': '🔗',
                    'error': '⚠️'
                }
    
    @classmethod
    def get_icon(cls, path: Path) -> str:
        """Get appropriate icon for file type with error handling"""
        # Ensure icons are loaded
        if cls._icons is None:
            cls.load_icons()
        
        try:
            # Validate path parameter
            if not isinstance(path, Path):
                logging.warning(f"Invalid path type: {type(path)}, expected Path")
                return cls._icons.get('error', '⚠️')
            
            # Handle different path types
            if path.is_dir():
                return cls._icons.get('directory', '📁')
            elif path.is_symlink():
                return cls._icons.get('symlink', '🔗')
            else:
                # Get file extension and return appropriate icon
                ext = path.suffix.lower()
                return cls._icons.get(ext, cls._icons.get('default', '📄'))
                
        except (OSError, PermissionError) as e:
            logging.warning(f"Error accessing path {path}: {e}")
            return cls._icons.get('error', '⚠️')
        except Exception as e:
            logging.error(f"Unexpected error getting icon for {path}: {e}")
            return cls._icons.get('error', '⚠️')
    
    @classmethod
    def is_loaded(cls) -> bool:
        """Check if icons are loaded"""
        return cls._icons is not None
    
    @classmethod
    def get_available_extensions(cls) -> list:
        """Get list of supported file extensions"""
        if cls._icons is None:
            cls.load_icons()
        
        return [ext for ext in cls._icons.keys() 
                if ext.startswith('.') and ext not in ['default', 'directory', 'symlink', 'error']]