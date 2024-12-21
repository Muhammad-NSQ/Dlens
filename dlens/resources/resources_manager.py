import json
import importlib.resources
from pathlib import Path
from typing import Union, Dict

class ResourcesManager:
    """Centralized manager to load and store resources like icons, themes, templates etc."""
    
    _resources = {}  # Store loaded resources here
    
    @classmethod
    def _load_json_resource(cls, resource_name: str, json_path: Union[str, Path] = None) -> Dict:
        """Load a JSON resource and cache it."""
        if resource_name in cls._resources:
            return cls._resources[resource_name]
        
        if json_path is None:
            try:
                with importlib.resources.open_text('dlens.resources', resource_name, encoding='utf-8') as f:
                    data = json.load(f)
                    cls._resources[resource_name] = data
                    return data
            except FileNotFoundError:
                raise FileNotFoundError(f"{resource_name} configuration file not found in package resources.")
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON format in {resource_name}.")
        else:
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cls._resources[resource_name] = data
                    return data
            except FileNotFoundError:
                raise FileNotFoundError(f"{resource_name} configuration file not found: {json_path}")
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON format in {resource_name}.")
    
    @classmethod
    def get_template(cls, template_name: str) -> str:
        """Get template content from resources."""
        if template_name in cls._resources:
            return cls._resources[template_name]
        
        try:
            with importlib.resources.open_text('dlens.resources.templates', template_name, encoding='utf-8') as f:
                template_content = f.read()
                cls._resources[template_name] = template_content
                return template_content
        except FileNotFoundError:
            raise FileNotFoundError(f"Template {template_name} not found in package resources.")
    
    @classmethod
    def get_icons(cls, json_path: Union[str, Path] = None) -> Dict:
        """Get icons data."""
        return cls._load_json_resource('icons.json', json_path)
    
    @classmethod
    def get_themes(cls, json_path: Union[str, Path] = None) -> Dict:
        """Get themes data."""
        return cls._load_json_resource('themes.json', json_path)