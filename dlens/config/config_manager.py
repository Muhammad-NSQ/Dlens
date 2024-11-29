import os
import json
import click
from typing import Dict, Any

class ConfigManager:
    """
    Manages configuration for DLens, supporting persistent storage and manipulation.
    """
    DEFAULT_CONFIG = {
        # DirectoryMapper default configurations
        'max_preview': 3,
        'root_preview': 5,
        'show_hidden': False,
        'max_depth': None,
        'color': True,
        'filter': [],
        'exclude': [],
        'show_details': False,
        'output_format': 'text',
        'sort_by': 'name',
        'follow_symlinks': False,
        'log_path': None,
        'theme': 'default',
        'show_stats': False,
        'progress': True,
        'icons': True
    }

    @classmethod
    def _get_config_path(cls) -> str:
        """
        Get the path to the configuration file.
        Supports cross-platform config storage.
        """
        config_dir = os.path.expanduser('~/.config/dlens')
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, 'config.json')

    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """
        Load configuration from file, merging with defaults.
        """
        config_path = cls._get_config_path()
        try:
            with open(config_path, 'r') as f:
                saved_config = json.load(f)
                return {**cls.DEFAULT_CONFIG, **saved_config}
        except (FileNotFoundError, json.JSONDecodeError):
            return cls.DEFAULT_CONFIG.copy()

    @classmethod
    def save_config(cls, config: Dict[str, Any]):
        """
        Save configuration to file.
        """
        config_path = cls._get_config_path()
        # Remove keys with None or default values
        clean_config = {
            k: v for k, v in config.items() 
            if v is not None and v != cls.DEFAULT_CONFIG.get(k)
        }
        
        with open(config_path, 'w') as f:
            json.dump(clean_config, f, indent=4)

    @classmethod
    def reset_config(cls):
        """
        Reset configuration to default values.
        """
        config_path = cls._get_config_path()
        try:
            os.remove(config_path)
        except FileNotFoundError:
            pass

    @classmethod
    def update_config(cls, updates: Dict[str, Any]):
        """
        Update specific configuration values.
        """
        current_config = cls.load_config()
        current_config.update({k: v for k, v in updates.items() if v is not None})
        cls.save_config(current_config)

def config_command(action, key=None, value=None):
    """
    Handle configuration management CLI actions.
    """
    if action == 'view':
        config = ConfigManager.load_config()
        for k, v in config.items():
            click.echo(f"{k}: {v}")
    
    elif action == 'reset':
        ConfigManager.reset_config()
        click.echo("Configuration reset to default.")
    
    elif action == 'set':
        if not key or value is None:
            click.echo("Error: Both key and value are required.")
            return
        
        try:
            # Type conversion logic
            if key in ['max_preview', 'root_preview', 'max_depth']:
                value = int(value)
            elif key in ['show_hidden', 'color', 'show_details', 'follow_symlinks', 'show_stats', 'progress', 'icons']:
                value = value.lower() in ['true', '1', 'yes']
            elif key in ['filter', 'exclude']:
                value = value.split(',') if value else []
        except ValueError:
            click.echo(f"Invalid value for {key}.")
            return
        
        ConfigManager.update_config({key: value})
        click.echo(f"Set {key} to {value}")