"""
Directory Lens (dlens) - Enhanced Directory Mapping Tool
Command Line Interface
"""
import click
import os
import sys
import json
from rich.console import Console
from rich.table import Table
from pathlib import Path

from dlens.config.config_manager import ConfigManager, config_command
from dlens.core.directory_mapper import DirectoryMapper
from dlens.core.search_handler import SearchHandler
from dlens.ui.theme_manager import ThemeManager
from dlens.ui.file_icons import FileTypeIcons
from dlens.utils.exporters import SearchExporter
from dlens.resources.resources_manager import ResourcesManager


def _merge_config_with_kwargs(saved_config: dict, kwargs: dict) -> dict:
    """Merge saved config with CLI kwargs, prioritizing non-None CLI values"""
    final_config = saved_config.copy()
    
    for key, value in kwargs.items():
        saved_value = saved_config.get(key)
        
        if isinstance(saved_value, list) or isinstance(value, (list, tuple)):
            if value:
                final_config[key] = list(set(saved_value or []) | set(value))
            else:
                final_config[key] = saved_value
        elif value is not None and not (isinstance(value, bool) and value is False):
            final_config[key] = value
            
    return final_config

@click.group(context_settings=dict(help_option_names=['-h', '--help']))
def cli():
    """DLens - Enhanced Directory Mapping Tool"""
    pass

@cli.command()
@click.argument('path', type=click.Path(exists=True), default=os.getcwd(), required=False)
@click.option('--max-preview', type=int, help='Maximum items per directory')
@click.option('--root-preview', type=int, help='Maximum items in root')
@click.option('--depth', type=int, help='Maximum recursion depth')
@click.option('--show-hidden/--no-hidden', help='Include hidden files')
@click.option('--filter', multiple=True, help='Filter by extensions')
@click.option('--exclude', multiple=True, help='Exclude extensions')
@click.option('--show-details/--no-details', help='Show file metadata')
@click.option('--output-format', type=click.Choice(['text', 'json', 'markdown', 'html']))
@click.option('--color/--no-color', help='Enable colored output')
@click.option('--sort', type=click.Choice(['name', 'size', 'date']))
@click.option('--follow-symlinks/--no-symlinks', help='Follow symbolic links')
@click.option('--log', type=click.Path(), help='Log file path')
@click.option('--theme', help='Theme name')
@click.option('--theme-path', type=click.Path(exists=True), help='Custom theme path')
@click.option('--show-stats/--no-stats', help='Show directory statistics')
@click.option('--progress/--no-progress', help='Show progress')
@click.option('--icons/--no-icons', help='Show file icons')

def map(path, **kwargs):
    """Map directory structure with optional configurations."""
    saved_config = ConfigManager.load_config()
    final_config = _merge_config_with_kwargs(saved_config, kwargs)
    
    ResourcesManager.get_icons()
    FileTypeIcons.load_icons()
    
    theme_manager = ThemeManager(
        theme_name=final_config.get('theme'),
        theme_path=final_config.get('theme_path')
    )
    
    mapper = DirectoryMapper(
        path=path,
        max_preview=final_config['max_preview'],
        root_preview=final_config['root_preview'],
        max_depth=final_config.get('depth'),
        show_hidden=final_config['show_hidden'],
        filter_ext=final_config['filter'],
        exclude_ext=final_config['exclude'],
        show_details=final_config['show_details'],
        color=final_config['color'],
        output_format=final_config['output_format'],
        sort_by=final_config['sort_by'],
        follow_symlinks=final_config['follow_symlinks'],
        log_path=final_config.get('log_path'),
        theme=theme_manager.theme,
        show_stats=final_config['show_stats'],
        show_progress=final_config['progress'],
        show_icons=final_config['icons']
    )
    
    mapper.export()

@cli.command()
@click.argument('pattern')
@click.argument('path', type=click.Path(exists=True), default=os.getcwd(), required=False)
@click.option('--regex/--no-regex', help='Use regex pattern')
@click.option('--case-sensitive/--no-case-sensitive', help='Case-sensitive search')
@click.option('--max-results', type=int, help='Maximum results')
@click.option('--max-depth', type=int, help='Maximum search depth')
@click.option('--follow-symlinks/--no-symlinks', help='Follow symbolic links')
@click.option('--show-hidden/--no-hidden', help='Include hidden files')
@click.option('--parallel/--no-parallel', help='Use parallel search')
@click.option('--output-format', type=click.Choice(['text', 'json', 'csv', 'html']), help='Output format', default='text')
@click.option('--output-file', type=click.Path(), help='Output file path')
@click.option('--verbose/--no-verbose', help='Show detailed progress and errors', default=False)
def search(pattern, path, **kwargs):
    """Search for files and directories matching pattern."""
    try:
        # Load and merge configuration
        saved_config = ConfigManager.load_config()
        final_config = _merge_config_with_kwargs(saved_config, kwargs)
        
        # Initialize resources
        ResourcesManager.get_icons()
        FileTypeIcons.load_icons()
        
        # Setup search parameters
        handler = SearchHandler(
            root_path=path,
            pattern=pattern,
            use_regex=final_config.get('regex', False),
            case_sensitive=final_config.get('case_sensitive', True),
            max_results=final_config.get('max_results'),
            max_depth=final_config.get('max_depth'),
            follow_symlinks=final_config.get('follow_symlinks', False),
            show_hidden=final_config.get('show_hidden', False),
            verbose=final_config.get('verbose', False)
        )
        
        # Configure output options
        search_method = handler.search_parallel if final_config.get('parallel', True) else handler.search
        output_format = final_config.get('output_format', 'text')
        output_file = final_config.get('output_file')

        # Handle output file path
        if output_file:
            output_file = Path(output_file)
            if not output_file.is_absolute():
                output_file = Path.cwd() / output_file
                
            # Create parent directories if they don't exist
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Add extension if not provided
            if output_format in ['csv', 'html', 'json'] and not output_file.suffix:
                output_file = output_file.with_suffix(f'.{output_format}')
        
        # Collect search results
        results = list(search_method())
        
        if not results:
            click.echo("No results found.")
            # Show stats if verbose mode is on
            if final_config.get('verbose'):
                click.echo(f"Items scanned: {handler.stats.total_scanned}")
                if handler.stats.errors_count > 0:
                    click.echo(f"Errors encountered: {handler.stats.errors_count}")
                if handler.stats.skipped_count > 0:
                    click.echo(f"Items skipped: {handler.stats.skipped_count}")
            return
        
        # Handle different output formats
        if output_format == 'text':
            # Display results in terminal table
            table = Table(show_header=True)
            table.add_column("Type", style="bold")
            table.add_column("Path", style="cyan")
            table.add_column("Size", justify="right", style="light_green")
            table.add_column("Status", style="yellow") if final_config.get('verbose') else None
            
            for result in results:
                icon = FileTypeIcons.get_icon(result.path)
                size = f"{result.size:,} bytes" if result.size else "-"
                row = [icon, result.match_context, size]
                if final_config.get('verbose') and hasattr(result, 'error'):
                    row.append(result.error or "OK")
                table.add_row(*row)
                
            Console().print(table)
            
            # Show stats in verbose mode
            if final_config.get('verbose'):
                click.echo(f"\nSearch Statistics:")
                click.echo(f"Total matches: {len(results)}")
                click.echo(f"Items scanned: {handler.stats.total_scanned}")
                if handler.stats.errors_count > 0:
                    click.echo(f"Errors encountered: {handler.stats.errors_count}")
                if handler.stats.skipped_count > 0:
                    click.echo(f"Items skipped: {handler.stats.skipped_count}")
            
        elif output_format == 'json':
            # Format results as JSON with enhanced information
            json_results = {
                "results": [{
                    "path": str(result.path),
                    "is_directory": result.is_dir,
                    "size": result.size,
                    "match_context": result.match_context,
                    "icon": FileTypeIcons.get_icon(result.path),
                    "error": result.error if hasattr(result, 'error') else None
                } for result in results],
                "stats": {
                    "total_matches": len(results),
                    "total_scanned": handler.stats.total_scanned,
                    "errors_count": handler.stats.errors_count,
                    "skipped_count": handler.stats.skipped_count
                }
            }
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(json_results, f, indent=2)
                click.echo(f"Results exported to {output_file}")
            else:
                print(json.dumps(json_results, indent=2))
        
        elif output_format in ['csv', 'html']:
            # Handle CSV and HTML exports
            if not output_file:
                click.echo(f"Error: --output-file is required for {output_format} format")
                return
                
            try:
                exporter = SearchExporter(results)
                if output_format == 'csv':
                    exporter.export_csv(output_file)
                else:  # html
                    template = final_config.get('template', 'light')
                    exporter.export_html(
                        output_path=output_file,
                        template=f"search_results{'_dark' if template == 'dark' else ''}.html"
                    )
                
                click.echo(f"Results exported to {output_file}")
            except Exception as e:
                click.echo(f"Error exporting results: {str(e)}", err=True)
                return
                
    except Exception as e:
        click.echo(f"Error during search: {str(e)}", err=True)
        return

@cli.command()
@click.argument('action', type=click.Choice(['view', 'reset', 'set']), required=False)
@click.argument('key', required=False)
@click.argument('value', required=False)
def config(action, key=None, value=None):
    """Manage DLens configuration."""
    if not action:
        click.echo("Usage: dlens config [view|reset|set] [key] [value]")
        return
        
    if action == 'view':
        config = ConfigManager.load_config()
        for k, v in config.items():
            click.echo(f"{k}: {v}")
    
    elif action == 'reset':
        ConfigManager.reset_config()
        click.echo("Configuration reset to default.")
    
    elif action == 'set':
        if not key or value is None:
            click.echo("Error: Both key and value required for 'set'")
            return
        config_command('set', key, value)

def main():
    """Entry point for the CLI."""
    cli(prog_name="dlens")

if __name__ == '__main__':
    main()