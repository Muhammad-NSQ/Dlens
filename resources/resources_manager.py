import json
import importlib.resources
from pathlib import Path
from typing import Union, Dict

class ResourcesManager:
    """Centralized manager to load and store resources like icons, themes, etc."""
    
    _resources = {}  # Store loaded resources here
    
    @classmethod
    def _load_json_resource(cls, resource_name: str, json_path: Union[str, Path] = None) -> Dict:
        """Load a JSON resource and cache it."""
        if resource_name in cls._resources:
            return cls._resources[resource_name]  # Return cached resource
        
        if json_path is None:
            # Use importlib to load the resource from the package if no path is provided
            try:
                with importlib.resources.open_text('dlens.resources', resource_name, encoding='utf-8') as f:
                    data = json.load(f)
                    cls._resources[resource_name] = data  # Cache the loaded data
                    return data
            except FileNotFoundError:
                raise FileNotFoundError(f"{resource_name} configuration file not found in package resources.")
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON format in {resource_name}.")
        else:
            # Load from local file system if path is provided
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cls._resources[resource_name] = data  # Cache the loaded data
                    return data
            except FileNotFoundError:
                raise FileNotFoundError(f"{resource_name} configuration file not found: {json_path}")
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON format in {resource_name}.")
    
    @classmethod
    def get_icons(cls, json_path: Union[str, Path] = None) -> Dict:
        """Get icons data."""
        return cls._load_json_resource('icons.json', json_path)
    
    @classmethod
    def get_themes(cls, json_path: Union[str, Path] = None) -> Dict:
        """Get themes data."""
        return cls._load_json_resource('themes.json', json_path)