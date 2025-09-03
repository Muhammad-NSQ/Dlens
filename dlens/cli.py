# Key fixes for cli.py focusing on input validation and error handling

"""
Directory Lens (dlens) - Enhanced Directory Mapping Tool
Command Line Interface with improved error handling and validation
"""
import click
import os
import sys
import json
import logging
from pathlib import Path
from rich.console import Console

from dlens.config.config_manager import ConfigManager, config_command
from dlens.core.directory_mapper import DirectoryMapper
from dlens.core.search_handler import SearchHandler
from dlens.ui.theme_manager import ThemeManager
from dlens.ui.file_icons import FileTypeIcons
from dlens.utils.exporters import SearchExporter
from dlens.resources.resources_manager import ResourcesManager


def validate_path(ctx, param, value):
    """Validate path parameter"""
    if value is None:
        return os.getcwd()
    
    try:
        path = Path(value).resolve()
        if not path.exists():
            raise click.BadParameter(f"Path does not exist: {value}")
        if not path.is_dir():
            raise click.BadParameter(f"Path is not a directory: {value}")
        if not os.access(path, os.R_OK):
            raise click.BadParameter(f"No read permission for path: {value}")
        return str(path)
    except OSError as e:
        raise click.BadParameter(f"Invalid path: {e}")


def validate_positive_int(ctx, param, value):
    """Validate positive integer parameters"""
    if value is None:
        return value
    if value <= 0:
        raise click.BadParameter(f"{param.name} must be positive")
    if value > 10000:  # Reasonable upper limit
        raise click.BadParameter(f"{param.name} too large (max 10000)")
    return value


def validate_search_pattern(ctx, param, value):
    """Validate search pattern"""
    if not value or not value.strip():
        raise click.BadParameter("Search pattern cannot be empty")
    
    pattern = value.strip()
    if len(pattern) > 500:
        raise click.BadParameter("Search pattern too long (max 500 characters)")
    
    # Basic validation for dangerous patterns
    if any(char in pattern for char in ['<', '>', '|', '&', ';']) and not ctx.params.get('regex'):
        raise click.BadParameter("Pattern contains potentially dangerous characters")
    
    return pattern


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
def cli():
    """DLens - Enhanced Directory Mapping Tool"""
    pass


@cli.command()
@click.argument('path', type=click.Path(exists=True), default=os.getcwd(), 
               required=False, callback=validate_path)
@click.option('--max-preview', type=int, callback=validate_positive_int,
             help='Maximum items per directory')
@click.option('--root-preview', type=int, callback=validate_positive_int,
             help='Maximum items in root')
@click.option('--depth', type=int, callback=validate_positive_int,
             help='Maximum recursion depth')
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
    console = Console()
    
    try:
        # Load and validate configuration
        saved_config = ConfigManager.load_config()
        if not saved_config:
            console.print("[yellow]Warning: Using default configuration[/]")
            
        final_config = _merge_config_with_kwargs(saved_config, kwargs)
        
        # Initialize resources
        try:
            ResourcesManager.get_icons()
            FileTypeIcons.load_icons()
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load icons: {e}[/]")
        
        # Initialize theme
        try:
            theme_manager = ThemeManager(
                theme_name=final_config.get('theme'),
                theme_path=final_config.get('theme_path')
            )
        except Exception as e:
            console.print(f"[yellow]Warning: Theme error, using default: {e}[/]")
            theme_manager = ThemeManager()  # Use default theme
        
        # Create and run mapper
        with DirectoryMapper(
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
        ) as mapper:
            mapper.export()
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/]")
        sys.exit(1)
    except PermissionError as e:
        console.print(f"[red]Permission error: {e}[/]")
        sys.exit(1)
    except FileNotFoundError as e:
        console.print(f"[red]File not found: {e}[/]")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Configuration error: {e}[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/]")
        logging.error(f"Unexpected error in map command: {e}")
        sys.exit(1)


@cli.command()
@click.argument('pattern', callback=validate_search_pattern)
@click.argument('path', type=click.Path(exists=True), default=os.getcwd(), 
               required=False, callback=validate_path)
@click.option('--regex/--no-regex', help='Use regex pattern')
@click.option('--case-sensitive/--no-case-sensitive', help='Case-sensitive search')
@click.option('--max-results', type=int, callback=validate_positive_int, help='Maximum results')
@click.option('--max-depth', type=int, callback=validate_positive_int, help='Maximum search depth')
@click.option('--follow-symlinks/--no-symlinks', help='Follow symbolic links')
@click.option('--show-hidden/--no-hidden', help='Include hidden files')
@click.option('--parallel/--no-parallel', help='Use parallel search')
@click.option('--output-format', type=click.Choice(['text', 'json', 'csv', 'html']), 
             help='Output format', default='text')
@click.option('--output-file', type=click.Path(), help='Output file path for exports')
def search(pattern, path, **kwargs):
    """Search for files and directories matching pattern."""
    console = Console()
    
    try:
        # Load and validate configuration
        saved_config = ConfigManager.load_config()
        final_config = _merge_config_with_kwargs(saved_config, kwargs)
        
        # Initialize resources
        try:
            ResourcesManager.get_icons()
            FileTypeIcons.load_icons()
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load icons: {e}[/]")
        
        # Create search handler with context manager
        with SearchHandler(
            root_path=path,
            pattern=pattern,
            use_regex=final_config.get('regex', False),
            case_sensitive=final_config.get('case_sensitive', True),
            max_results=final_config.get('max_results'),
            max_depth=final_config.get('max_depth'),
            follow_symlinks=final_config.get('follow_symlinks', False),
            show_hidden=final_config.get('show_hidden', False)
        ) as handler:
            
            # Configure search method
            search_method = (handler.search_parallel 
                           if final_config.get('parallel', True) 
                           else handler.search)
            
            output_format = final_config.get('output_format', 'text')
            output_file = final_config.get('output_file')
            
            # Validate and prepare output file
            if output_file:
                output_file = _prepare_output_file(output_file, output_format)
            
            # Collect search results with progress indication
            console.print(f"[blue]Searching for '{pattern}' in {path}...[/]")
            results = list(search_method())
            
            if not results:
                console.print("[yellow]No results found.[/]")
                return
            
            console.print(f"[green]Found {len(results)} results[/]")
            
            # Handle output based on format
            _handle_search_output(results, output_format, output_file, console)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Search cancelled by user[/]")
        sys.exit(1)
    except ValueError as e:
        console.print(f"[red]Search pattern error: {e}[/]")
        sys.exit(1)
    except PermissionError as e:
        console.print(f"[red]Permission error: {e}[/]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Search error: {e}[/]")
        logging.error(f"Unexpected error in search command: {e}")
        sys.exit(1)


def _prepare_output_file(output_file: str, output_format: str) -> Path:
    """Prepare and validate output file path"""
    output_path = Path(output_file)
    
    # Make absolute path
    if not output_path.is_absolute():
        output_path = Path.cwd() / output_path
        
    # Create parent directories
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        raise click.BadParameter(f"Cannot create output directory: {e}")
        
    # Add extension if not provided
    if output_format in ['csv', 'html', 'json'] and not output_path.suffix:
        output_path = output_path.with_suffix(f'.{output_format}')
    
    return output_path


def _handle_search_output(results, output_format: str, output_file: Path, console: Console):
    """Handle search output in different formats"""
    try:
        if output_format == 'text':
            _display_text_results(results, console)
        elif output_format == 'json':
            _handle_json_output(results, output_file, console)
        elif output_format in ['csv', 'html']:
            _handle_export_output(results, output_format, output_file, console)
    except Exception as e:
        console.print(f"[red]Error handling output: {e}[/]")
        raise


def _display_text_results(results, console: Console):
    """Display search results in text format"""
    from rich.table import Table
    
    table = Table(show_header=True)
    table.add_column("Type", style="bold")
    table.add_column("Path", style="cyan")
    table.add_column("Size", justify="right", style="light_green")
    
    for result in results:
        try:
            icon = FileTypeIcons.get_icon(result.path)
            size = f"{result.size:,} bytes" if result.size else "-"
            table.add_row(icon, result.match_context, size)
        except Exception as e:
            # Skip problematic results but continue
            logging.warning(f"Error displaying result {result.path}: {e}")
            continue
            
    console.print(table)


def _handle_json_output(results, output_file: Path, console: Console):
    """Handle JSON output format"""
    json_results = []
    
    for result in results:
        try:
            json_results.append({
                "path": str(result.path),
                "is_directory": result.is_dir,
                "size": result.size,
                "match_context": result.match_context,
                "icon": FileTypeIcons.get_icon(result.path)
            })
        except Exception as e:
            logging.warning(f"Error processing result for JSON: {e}")
            continue
    
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_results, f, indent=2)
            console.print(f"[green]Results exported to {output_file}[/]")
        except (PermissionError, OSError) as e:
            raise click.ClickException(f"Cannot write to {output_file}: {e}")
    else:
        print(json.dumps(json_results, indent=2))


def _handle_export_output(results, output_format: str, output_file: Path, console: Console):
    """Handle CSV and HTML export formats"""
    if not output_file:
        raise click.ClickException(f"--output-file is required for {output_format} format")
        
    try:
        exporter = SearchExporter(results)
        if output_format == 'csv':
            exporter.export_csv(output_file)
        elif output_format == 'html':
            exporter.export_html(output_file)
        
        console.print(f"[green]Results exported to {output_file}[/]")
    except Exception as e:
        raise click.ClickException(f"Export failed: {e}")


def _merge_config_with_kwargs(saved_config: dict, kwargs: dict) -> dict:
    """Merge saved config with CLI kwargs, prioritizing non-None CLI values with validation"""
    final_config = saved_config.copy()
    
    for key, value in kwargs.items():
        if value is None:
            continue
            
        saved_value = saved_config.get(key)
        
        try:
            # Handle list/tuple merging
            if isinstance(saved_value, list) or isinstance(value, (list, tuple)):
                if value:
                    # Validate extensions
                    if key in ['filter', 'exclude']:
                        validated_exts = []
                        for ext in value:
                            if isinstance(ext, str) and len(ext.strip()) > 0:
                                clean_ext = ext.strip()
                                if not clean_ext.startswith('.'):
                                    clean_ext = '.' + clean_ext
                                validated_exts.append(clean_ext.lower())
                        final_config[key] = list(set((saved_value or []) + validated_exts))
                    else:
                        final_config[key] = list(set(saved_value or []) | set(value))
                else:
                    final_config[key] = saved_value
            # Handle other value types
            elif not (isinstance(value, bool) and value is False):
                final_config[key] = value
        except Exception as e:
            logging.warning(f"Error merging config for {key}: {e}")
            # Use saved value on error
            final_config[key] = saved_value
            
    return final_config


@cli.command()
@click.argument('action', type=click.Choice(['view', 'reset', 'set']), required=False)
@click.argument('key', required=False)
@click.argument('value', required=False)
def config(action, key=None, value=None):
    """Manage DLens configuration."""
    console = Console()
    
    try:
        if not action:
            console.print("[yellow]Usage: dlens config [view|reset|set] [key] [value][/]")
            return
            
        if action == 'view':
            config_data = ConfigManager.load_config()
            if not config_data:
                console.print("[yellow]No configuration found[/]")
                return
            
            console.print("[bold]Current Configuration:[/]")
            for k, v in sorted(config_data.items()):
                console.print(f"  {k}: [cyan]{v}[/]")
        
        elif action == 'reset':
            if ConfigManager.reset_config():
                console.print("[green]Configuration reset to default.[/]")
            else:
                console.print("[red]Error: Failed to reset configuration.[/]")
                sys.exit(1)
        
        elif action == 'set':
            if not key:
                console.print("[red]Error: Key is required for 'set' action.[/]")
                console.print("[yellow]Available keys:[/] " + 
                            ", ".join(sorted(ConfigManager.DEFAULT_CONFIG.keys())))
                sys.exit(1)
            if value is None:
                console.print("[red]Error: Value is required for 'set' action.[/]")
                sys.exit(1)
            
            if ConfigManager.update_config({key: value}):
                validated_value = ConfigManager.validate_config_value(key, value)
                console.print(f"[green]Set {key} to {validated_value}[/]")
            else:
                console.print(f"[red]Error: Failed to update {key}[/]")
                sys.exit(1)
                
    except Exception as e:
        console.print(f"[red]Configuration error: {e}[/]")
        logging.error(f"Config command error: {e}")
        sys.exit(1)


def main():
    """Entry point for the CLI with error handling."""
    try:
        cli(prog_name="dlens")
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        console = Console()
        console.print(f"[red]Fatal error: {e}[/]")
        logging.error(f"Fatal CLI error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()