"""
Directory Lens (dlens) - Enhanced Directory Mapping Tool
Command Line Interface
"""
import click
import os
import json
from dlens.core.directory_mapper import DirectoryMapper
from dlens.ui.theme_manager import ThemeManager
from dlens.ui.file_icons import FileTypeIcons
from dlens.resources.resources_manager import ResourcesManager

class DLensConfig:
    def __init__(self):
        self.theme_manager = ThemeManager()

pass_config = click.make_pass_decorator(DLensConfig, ensure=True)

@click.command(context_settings=dict(ignore_unknown_options=False))
@click.argument('path', type=click.Path(exists=True), default=os.getcwd())
@click.option('--max-preview', type=int, default=3, 
              help='Maximum number of items to preview per directory')
@click.option('--root-preview', type=int, default=5, 
              help='Maximum items to preview for the root directory')
@click.option('--depth', type=int, 
              help='Maximum depth to display')
@click.option('--show-hidden/--no-hidden', default=False, 
              help='Include hidden files and directories')
@click.option('--filter', multiple=True, 
              help='Filter files by extensions, e.g., .py .txt')
@click.option('--exclude', multiple=True, 
              help='Exclude files by extensions, e.g., .log')
@click.option('--show-details/--no-details', default=False, 
              help='Show file sizes and modification dates')
@click.option('--output-format', type=click.Choice(['text', 'json', 'markdown']), 
              default='text', help='Output format')
@click.option('--no-color', is_flag=True, 
              help='Disable color output')
@click.option('--sort', type=click.Choice(['name', 'size', 'date']), 
              default='name', help='Sort entries by')
@click.option('--follow-symlinks/--no-symlinks', default=False, 
              help='Follow symbolic links')
@click.option('--log', type=click.Path(), 
              help='Path to log file for tracking errors and access issues')
@click.option('--theme', 
              help='Theme name to use')
@click.option('--theme-path', type=click.Path(exists=True), 
              help='Path to custom themes file')
@click.option('--no-stats', is_flag=True, 
              help='Disable statistics collection and display')
@click.option('--no-progress', is_flag=True, 
              help='Disable progress tracking')
@click.option('--no-icons', is_flag=True, 
              help='Disable file type icons')
def cli(path, **kwargs):
    """DLens - Enhanced Directory Mapping Tool
    
    Run with a path and options to map directory structure.
    Examples:
        dlens                           # Map current directory
        dlens path/to/dir              # Map specific directory
        dlens --no-stats --sort date   # Map with options
        dlens path --show-hidden       # Map with path and options
    """
    # Load global resources
    ResourcesManager.get_icons()
    FileTypeIcons.load_icons()
    
    # Initialize theme manager with selected theme and optional custom theme path
    theme_manager = ThemeManager(
        theme_name=kwargs.get('theme'),
        theme_path=kwargs.get('theme_path')
    )
    
    # If theme not found, warn user
    if kwargs.get('theme') and theme_manager.theme['name'] == 'default':
        click.echo(f"Warning: Theme '{kwargs['theme']}' not found, using default theme", err=True)
   
    # Create and run the mapper
    mapper = DirectoryMapper(
        path=path,
        max_preview=kwargs.get('max_preview'),
        root_preview=kwargs.get('root_preview'),
        max_depth=kwargs.get('depth'),
        show_hidden=kwargs.get('show_hidden'),
        filter_ext=kwargs.get('filter'),
        exclude_ext=kwargs.get('exclude'),
        show_details=kwargs.get('show_details'),
        color=not kwargs.get('no_color'),
        output_format=kwargs.get('output_format'),
        sort_by=kwargs.get('sort'),
        follow_symlinks=kwargs.get('follow_symlinks'),
        log_path=kwargs.get('log'),
        theme=theme_manager.theme,  
        show_stats=not kwargs.get('no_stats'),
        show_progress=not kwargs.get('no_progress'),
        show_icons=not kwargs.get('no_icons')
    )
    
    mapper.export()

def main():
    """Entry point for the CLI."""
    cli(prog_name="dlens")

if __name__ == '__main__':
    main()