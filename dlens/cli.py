"""
Directory Lens (dlens) - Enhanced Directory Mapping Tool
Command Line Interface
"""
import click
import os
import sys
from dlens.config.config_manager import ConfigManager, config_command
from dlens.core.directory_mapper import DirectoryMapper
from dlens.ui.theme_manager import ThemeManager
from dlens.ui.file_icons import FileTypeIcons
from dlens.resources.resources_manager import ResourcesManager

@click.group(context_settings=dict(help_option_names=['-h', '--help']))
def cli():
    """DLens - Enhanced Directory Mapping Tool
    
    Subcommands:
    - map: Map directory structure
    - config: Manage DLens configuration
    """
    pass

@cli.command()
@click.argument('path', type=click.Path(exists=True), default=os.getcwd(), required=False)
@click.option('--max-preview', type=int, 
              help='Maximum number of items to preview per directory')
@click.option('--root-preview', type=int, 
              help='Maximum items to preview for the root directory')
@click.option('--depth', type=int, 
              help='Maximum depth to display')
@click.option('--show-hidden/--no-hidden', 
              help='Include hidden files and directories')
@click.option('--filter', multiple=True, 
              help='Filter files by extensions, e.g., .py .txt')
@click.option('--exclude', multiple=True, 
              help='Exclude files by extensions, e.g., .log')
@click.option('--show-details/--no-details', 
              help='Show file sizes and modification dates')
@click.option('--output-format', type=click.Choice(['text', 'json', 'markdown']), 
              help='Output format')
@click.option('--color/--no-color', 
              help='Enable/Disable color output')
@click.option('--sort', type=click.Choice(['name', 'size', 'date']), 
              help='Sort entries by')
@click.option('--follow-symlinks/--no-symlinks', 
              help='Follow symbolic links')
@click.option('--log', type=click.Path(), 
              help='Path to log file for tracking errors and access issues')
@click.option('--theme', 
              help='Theme name to use')
@click.option('--theme-path', type=click.Path(exists=True), 
              help='Path to custom themes file')
@click.option('--show-stats/--no-stats', 
              help='Enable/Disable statistics collection')
@click.option('--progress/--no-progress', 
              help='Enable/Disable progress tracking')
@click.option('--icons/--no-icons', 
              help='Enable/Disable file type icons')
def map(path, **kwargs):
    """Map directory structure with optional configurations."""
    # Load saved configuration
    saved_config = ConfigManager.load_config()
    
    # # Merge saved config with current kwargs (current kwargs take precedence)
    final_config = saved_config.copy()  # Start with saved config

    # Merge command-line options, prioritizing non-None values
    # Merge command-line options, prioritizing non-None values
    for key, value in kwargs.items():
        saved_value = saved_config.get(key)

        # Handle list-like arguments
        if isinstance(saved_value, list) or isinstance(value, (list, tuple)):
            if value:  # If CLI provides new values
                # Merge saved values and new values, ensuring no duplicates
                final_config[key] = list(set(saved_value or []) | set(value))
            else:
                # Use saved values if no new values are provided
                final_config[key] = saved_value
        elif value is not None and not (isinstance(value, bool) and value is False):
            # For non-list arguments, CLI values take precedence
            final_config[key] = value
    # Load global resources
    ResourcesManager.get_icons()
    FileTypeIcons.load_icons()
    
    # Initialize theme manager
    theme_manager = ThemeManager(
        theme_name=final_config.get('theme'),
        theme_path=final_config.get('theme_path')
    )
   
    # Create and run the mapper
    mapper = DirectoryMapper(
        path=path,
        max_preview=final_config.get('max_preview'),
        root_preview=final_config.get('root_preview'),
        max_depth=final_config.get('depth'),
        show_hidden=final_config.get('show_hidden'),
        filter_ext=final_config.get('filter', []),
        exclude_ext=final_config.get('exclude', []),
        show_details=final_config.get('show_details'),
        color=final_config.get('color'),
        output_format=final_config.get('output_format'),
        sort_by=final_config.get('sort'),
        follow_symlinks=final_config.get('follow_symlinks'),
        log_path=final_config.get('log'),
        theme=theme_manager.theme,  
        show_stats=final_config.get('show_stats'),
        show_progress=final_config.get('progress'),
        show_icons=final_config.get('icons')
    )
    
    mapper.export()

@cli.command()
@click.argument('action', type=click.Choice(['view', 'reset']), required=False)
@click.option('--set', nargs=2, multiple=True, help='Set specific configuration values')
def config(action, set):
    """Manage DLens configuration.
    
    Actions:
    - view: Show current configuration
    - reset: Reset to default configuration
    - --set key value: Set specific configuration values
    """
    if action:
        config_command(action)
    
    if set:
        for key, value in set:
            config_command('set', key, value)

def main():
    """Entry point for the CLI."""
    cli(prog_name="dlens")

if __name__ == '__main__':
    main()