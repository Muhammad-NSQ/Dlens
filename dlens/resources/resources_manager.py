import json
import importlib.resources
import logging
import threading
from pathlib import Path
from typing import Union, Dict

class ResourcesManager:
    """Centralized manager to load and store resources like icons, themes, templates etc."""
    
    _resources = {}  # Store loaded resources here
    _lock = threading.Lock()  # Thread safety for shared resources
    
    @classmethod
    def _load_json_resource(cls, resource_name: str, json_path: Union[str, Path] = None) -> Dict:
        """Load a JSON resource and cache it with proper error handling."""
        with cls._lock:  # Thread safety
            if resource_name in cls._resources:
                return cls._resources[resource_name]
        
            try:
                if json_path is None:
                    # Use context manager for resource loading
                    with importlib.resources.open_text('dlens.resources', resource_name, encoding='utf-8') as f:
                        data = json.load(f)
                else:
                    # Use context manager for file loading
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                
                cls._resources[resource_name] = data
                return data
                
            except FileNotFoundError as e:
                logging.error(f"Resource file not found: {resource_name} - {e}")
                raise FileNotFoundError(f"{resource_name} configuration file not found.")
            except json.JSONDecodeError as e:
                logging.error(f"Invalid JSON in resource: {resource_name} - {e}")
                raise ValueError(f"Invalid JSON format in {resource_name}.")
            except PermissionError as e:
                logging.error(f"Permission denied accessing: {resource_name} - {e}")
                raise PermissionError(f"Permission denied accessing {resource_name}.")
            except OSError as e:
                logging.error(f"OS error loading resource: {resource_name} - {e}")
                raise OSError(f"System error loading {resource_name}: {e}")
    
    @classmethod
    def get_template(cls, template_name: str) -> str:
        """Get template content from resources with proper error handling."""
        with cls._lock:  # Thread safety
            if template_name in cls._resources:
                return cls._resources[template_name]
        
            try:
                with importlib.resources.open_text('dlens.resources.templates', template_name, encoding='utf-8') as f:
                    template_content = f.read()
                    cls._resources[template_name] = template_content
                    return template_content
            except FileNotFoundError as e:
                logging.error(f"Template not found: {template_name} - {e}")
                raise FileNotFoundError(f"Template {template_name} not found in package resources.")
            except PermissionError as e:
                logging.error(f"Permission denied accessing template: {template_name} - {e}")
                raise PermissionError(f"Permission denied accessing template {template_name}.")
            except OSError as e:
                logging.error(f"OS error loading template: {template_name} - {e}")
                raise OSError(f"System error loading template {template_name}: {e}")
    
    @classmethod
    def get_icons(cls, json_path: Union[str, Path] = None) -> Dict:
        """Get icons data with error handling."""
        return cls._load_json_resource('icons.json', json_path)
    
    @classmethod
    def get_themes(cls, json_path: Union[str, Path] = None) -> Dict:
        """Get themes data with error handling."""
        return cls._load_json_resource('themes.json', json_path)