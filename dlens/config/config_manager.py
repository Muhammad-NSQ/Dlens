import os
import json
import click
from typing import Dict, Any

class ConfigManager:
    """
    Manages configuration for DLens, supporting persistent storage and manipulation.
    """
    DEFAULT_CONFIG = {
        # DirectoryMapper core settings
        'max_preview': 3,            # Maximum items to show per directory
        'root_preview': 5,           # Maximum items to show in root directory
        'max_depth': None,           # Maximum directory traversal depth (None for unlimited)
        'sort_by': 'name',          # Sort criteria: 'name', 'size', or 'date'
        
        # File filtering options
        'show_hidden': False,        # Show hidden files and directories
        'filter': [],               # List of file extensions to include (empty = all)
        'exclude': [],              # List of file extensions to exclude
        'follow_symlinks': False,    # Follow symbolic links during traversal
        
        # Display settings
        'show_details': False,       # Show file/directory details (size, date)
        'output_format': 'text',     # Output format: 'text', 'json', or 'markdown'
        'color': True,              # Enable colored output
        'icons': True,              # Show file and directory icons
        'theme': 'default',         # UI theme name
        'theme_path': None,         # Custom theme file path
        
        # Feature toggles
        'show_stats': False,         # Show directory statistics
        'progress': True,           # Show progress during mapping
        
        # Search-specific settings
        'parallel': True,           # Enable parallel processing for search
        'case_sensitive': False,    # Case-sensitive search
        'max_results': None,        # Maximum search results (None for unlimited)
        'search_depth': None,       # Maximum search depth (None for unlimited)
        
        # Export settings
        'output_file': None,        # Output file path for exports
        'template': 'light',        # HTML template style ('light' or 'dark')
        'log_path': None,          # Log file path
        
        # Performance settings
        'chunk_size': 1000,        # Chunk size for parallel processing
        'max_workers': None,        # Maximum worker threads (None = CPU count)
        
        # UI customization
        'progress_style': 'bar',    # Progress display style: 'bar' or 'spinner'
        'date_format': '%Y-%m-%d %H:%M:%S',  # Date format for file details
        
        # Advanced settings
        'follow_mounts': False,     # Follow mounted filesystems
        'skip_permission_errors': True,  # Continue on permission errors
        'memory_limit': None,       # Memory limit in MB (None for unlimited)
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