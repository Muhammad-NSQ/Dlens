import os
import json
import click
import logging
from typing import Dict, Any, Union
from pathlib import Path

class ConfigManager:
    """
    Manages configuration for DLens with input validation and error handling.
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

    # Define valid values for validation
    VALID_VALUES = {
        'sort_by': ['name', 'size', 'date'],
        'output_format': ['text', 'json', 'markdown', 'html'],
        'theme': ['default', 'ocean', 'forest', 'pastel', 'monochrome', 'dark'],
        'template': ['light', 'dark'],
        'progress_style': ['bar', 'spinner']
    }

    @classmethod
    def _get_config_path(cls) -> str:
        """
        Get the path to the configuration file with proper error handling.
        """
        try:
            config_dir = os.path.expanduser('~/.config/dlens')
            os.makedirs(config_dir, exist_ok=True)
            return os.path.join(config_dir, 'config.json')
        except (OSError, PermissionError) as e:
            logging.error(f"Cannot create config directory: {e}")
            # Fallback to current directory
            return os.path.join(os.getcwd(), '.dlens_config.json')

    @classmethod
    def validate_config_value(cls, key: str, value: Any) -> Any:
        """
        Validate and sanitize configuration values.
        """
        try:
            # Integer validations
            if key in ['max_preview', 'root_preview']:
                if value is None:
                    return cls.DEFAULT_CONFIG[key]
                val = int(value)
                return max(1, min(100, val))  # Clamp between 1-100
                
            elif key in ['max_depth', 'max_results', 'search_depth']:
                if value is None or value == 'None':
                    return None
                val = int(value)
                return max(1, min(1000, val)) if val > 0 else None
                
            elif key == 'chunk_size':
                if value is None:
                    return cls.DEFAULT_CONFIG[key]
                val = int(value)
                return max(10, min(10000, val))  # Reasonable chunk size
                
            elif key == 'max_workers':
                if value is None or value == 'None':
                    return None
                val = int(value)
                return max(1, min(32, val)) if val > 0 else None
                
            elif key == 'memory_limit':
                if value is None or value == 'None':
                    return None
                val = int(value)
                return max(64, min(32768, val)) if val > 0 else None  # 64MB to 32GB
                
            # Boolean validations
            elif key in ['show_hidden', 'follow_symlinks', 'show_details', 'color', 
                        'icons', 'show_stats', 'progress', 'parallel', 'case_sensitive',
                        'follow_mounts', 'skip_permission_errors']:
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ['true', '1', 'yes', 'on']
                return bool(value)
                
            # String validations with allowed values
            elif key in cls.VALID_VALUES:
                if value not in cls.VALID_VALUES[key]:
                    logging.warning(f"Invalid value '{value}' for {key}, using default")
                    return cls.DEFAULT_CONFIG[key]
                return value
                
            # List validations
            elif key in ['filter', 'exclude']:
                if isinstance(value, str):
                    if not value.strip():
                        return []
                    # Split by comma and clean up
                    extensions = [ext.strip() for ext in value.split(',')]
                    # Validate extensions format
                    validated = []
                    for ext in extensions:
                        if ext and len(ext) <= 10:  # Reasonable extension length
                            if not ext.startswith('.'):
                                ext = '.' + ext
                            validated.append(ext.lower())
                    return validated
                elif isinstance(value, list):
                    return [ext.lower() for ext in value if isinstance(ext, str) and len(ext) <= 10]
                return []
                
            # Path validations
            elif key in ['theme_path', 'output_file', 'log_path']:
                if value is None or value == 'None':
                    return None
                path_str = str(value).strip()
                if not path_str:
                    return None
                # Basic path validation
                try:
                    path = Path(path_str)
                    if len(str(path)) > 500:  # Reasonable path length limit
                        logging.warning(f"Path too long for {key}, ignoring")
                        return None
                    return str(path)
                except Exception:
                    logging.warning(f"Invalid path for {key}: {path_str}")
                    return None
                    
            # Date format validation
            elif key == 'date_format':
                if not isinstance(value, str) or len(value) > 50:
                    return cls.DEFAULT_CONFIG[key]
                # Basic validation - try to format a date
                try:
                    from datetime import datetime
                    datetime.now().strftime(value)
                    return value
                except Exception:
                    logging.warning(f"Invalid date format: {value}")
                    return cls.DEFAULT_CONFIG[key]
                    
            # Default case - return as-is if it passes basic checks
            else:
                return value
                
        except (ValueError, TypeError) as e:
            logging.warning(f"Error validating {key}={value}: {e}")
            return cls.DEFAULT_CONFIG.get(key)

    @classmethod
    def load_config(cls) -> Dict[str, Any]:
        """
        Load configuration from file with error handling and validation.
        """
        config_path = cls._get_config_path()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                saved_config = json.load(f)
                
            # Validate loaded config
            if not isinstance(saved_config, dict):
                logging.warning("Config file contains invalid data, using defaults")
                return cls.DEFAULT_CONFIG.copy()
                
            # Merge with defaults and validate each value
            merged_config = cls.DEFAULT_CONFIG.copy()
            for key, value in saved_config.items():
                if key in cls.DEFAULT_CONFIG:
                    merged_config[key] = cls.validate_config_value(key, value)
                else:
                    logging.warning(f"Unknown config key ignored: {key}")
                    
            return merged_config
            
        except FileNotFoundError:
            logging.info("No config file found, using defaults")
            return cls.DEFAULT_CONFIG.copy()
        except json.JSONDecodeError as e:
            logging.error(f"Invalid JSON in config file: {e}")
            return cls.DEFAULT_CONFIG.copy()
        except PermissionError as e:
            logging.error(f"Permission denied reading config: {e}")
            return cls.DEFAULT_CONFIG.copy()
        except OSError as e:
            logging.error(f"OS error reading config: {e}")
            return cls.DEFAULT_CONFIG.copy()

    @classmethod
    def save_config(cls, config: Dict[str, Any]) -> bool:
        """
        Save configuration to file with validation and error handling.
        """
        if not isinstance(config, dict):
            logging.error("Config must be a dictionary")
            return False
            
        config_path = cls._get_config_path()
        
        try:
            # Validate all config values before saving
            validated_config = {}
            for key, value in config.items():
                if key in cls.DEFAULT_CONFIG:
                    validated_config[key] = cls.validate_config_value(key, value)
                    
            # Remove keys with default values to keep config file clean
            clean_config = {
                k: v for k, v in validated_config.items() 
                if v is not None and v != cls.DEFAULT_CONFIG.get(k)
            }
            
            # Atomic write - write to temp file first
            temp_path = config_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(clean_config, f, indent=4, sort_keys=True)
                
            # Move temp file to final location
            os.replace(temp_path, config_path)
            logging.info(f"Config saved to {config_path}")
            return True
            
        except PermissionError as e:
            logging.error(f"Permission denied writing config: {e}")
            return False
        except OSError as e:
            logging.error(f"OS error writing config: {e}")
            return False
        except Exception as e:
            logging.error(f"Unexpected error saving config: {e}")
            # Clean up temp file if it exists
            temp_path = config_path + '.tmp'
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
            return False

    @classmethod
    def reset_config(cls) -> bool:
        """
        Reset configuration to default values.
        """
        config_path = cls._get_config_path()
        try:
            if os.path.exists(config_path):
                os.remove(config_path)
            logging.info("Configuration reset to defaults")
            return True
        except (FileNotFoundError, PermissionError, OSError) as e:
            logging.error(f"Error resetting config: {e}")
            return False

    @classmethod
    def update_config(cls, updates: Dict[str, Any]) -> bool:
        """
        Update specific configuration values with validation.
        """
        if not isinstance(updates, dict):
            logging.error("Updates must be a dictionary")
            return False
            
        current_config = cls.load_config()
        
        # Validate and apply updates
        valid_updates = {}
        for key, value in updates.items():
            if key in cls.DEFAULT_CONFIG:
                valid_updates[key] = cls.validate_config_value(key, value)
            else:
                logging.warning(f"Unknown config key ignored: {key}")
                
        current_config.update(valid_updates)
        return cls.save_config(current_config)


def config_command(action, key=None, value=None):
    """
    Handle configuration management CLI actions with proper validation.
    """
    try:
        if action == 'view':
            config = ConfigManager.load_config()
            if not config:
                click.echo("No configuration found")
                return
            for k, v in sorted(config.items()):
                click.echo(f"{k}: {v}")
        
        elif action == 'reset':
            if ConfigManager.reset_config():
                click.echo("Configuration reset to default.")
            else:
                click.echo("Error: Failed to reset configuration.", err=True)
        
        elif action == 'set':
            if not key:
                click.echo("Error: Key is required for 'set' action.", err=True)
                return
            if value is None:
                click.echo("Error: Value is required for 'set' action.", err=True)
                return
                
            # Validate key exists
            if key not in ConfigManager.DEFAULT_CONFIG:
                click.echo(f"Error: Unknown configuration key '{key}'", err=True)
                valid_keys = ', '.join(sorted(ConfigManager.DEFAULT_CONFIG.keys()))
                click.echo(f"Valid keys: {valid_keys}")
                return
            
            # Update configuration
            if ConfigManager.update_config({key: value}):
                validated_value = ConfigManager.validate_config_value(key, value)
                click.echo(f"Set {key} to {validated_value}")
            else:
                click.echo(f"Error: Failed to update {key}", err=True)
                
        else:
            click.echo("Error: Invalid action. Use 'view', 'reset', or 'set'.", err=True)
            
    except Exception as e:
        logging.error(f"Config command error: {e}")
        click.echo(f"Error: {e}", err=True)