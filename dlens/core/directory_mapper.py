import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Union
from jinja2 import Template
from contextlib import contextmanager

from rich.console import Console
from rich.tree import Tree
from rich.table import Table

from dlens.core.platform_handler import PlatformHandler
from dlens.core.progress_tracker import ProgressTracker
from dlens.utils.stats_collector import DirectoryStats
from dlens.ui.file_icons import FileTypeIcons
from dlens.utils.size_formatter import SizeFormatter
from dlens.resources.resources_manager import ResourcesManager


class MapFormatter:
    """Handles formatting of directory mapping data into different output formats"""
    
    @staticmethod
    def format_rich_tree(
        dir_path: Path,
        scan_func,
        theme: dict,
        max_preview: int,
        root_preview: int,
        max_depth: Optional[int],
        show_details: bool,
        show_icons: bool,
        color: bool,
        platform_handler
    ) -> Tree:
        """Format directory structure as a Rich tree"""
        def add_tree_branch(parent: Tree, dir_path: Path, level: int = 0) -> None:
            if max_depth is not None and level >= max_depth:
                return

            try:
                scan_result = scan_func(dir_path)
                dirs = scan_result['dirs']
                files = scan_result['files']

                current_max_preview = root_preview if level == 0 else max_preview

                # Add directories
                for d in dirs[:current_max_preview]:
                    try:
                        style = theme.get('directory', 'bold light_green') if color else ""
                        icon = FileTypeIcons.get_icon(d) if show_icons else ""
                        name = f"{icon} {d.name}/" if show_icons else f"{d.name}/"
                        subtree = parent.add(f"[{style}]{name}[/]" if style else name)
                        add_tree_branch(subtree, d, level + 1)
                    except Exception as e:
                        logging.warning(f"Error adding directory {d}: {str(e)}")

                if len(dirs) > current_max_preview:
                    more_style = theme.get('more_items', 'dim')
                    parent.add(
                        f"[{more_style}](... {len(dirs) - current_max_preview} more folders)[/]"
                        if color else
                        f"(... {len(dirs) - current_max_preview} more folders)"
                    )

                # Add files
                for f in files[:current_max_preview]:
                    try:
                        if show_details:
                            file_info = platform_handler.get_file_info(f)
                            size = SizeFormatter.format_size(file_info.get('size', 0))
                            modified = file_info.get('modified')
                            modified_str = modified.strftime('%Y-%m-%d %H:%M:%S') if modified else 'unknown'
                            details = (
                                f" [italic {theme.get('details', 'dim cyan')}]"
                                f"(size: {size}, modified: {modified_str})[/]"
                                if color else
                                f" (size: {size}, modified: {modified_str})"
                            )
                            icon = FileTypeIcons.get_icon(f) if show_icons else ""
                            display_name = f"{icon} {f.name}{details}" if show_icons else f"{f.name}{details}"
                        else:
                            icon = FileTypeIcons.get_icon(f) if show_icons else ""
                            display_name = f"{icon} {f.name}" if show_icons else f"{f.name}"

                        style = theme.get('file', 'bold yellow') if color else ""
                        parent.add(f"[{style}]{display_name}[/]" if style else display_name)
                    except Exception as e:
                        logging.warning(f"Error adding file {f}: {str(e)}")

                if len(files) > current_max_preview:
                    more_style = theme.get('more_items', 'dim')
                    parent.add(
                        f"[{more_style}](... {len(files) - current_max_preview} more files)[/]"
                        if color else
                        f"(... {len(files) - current_max_preview} more files)"
                    )
            except Exception as e:
                logging.error(f"Error processing directory {dir_path}: {str(e)}")

        try:
            style = theme.get('root', 'bold red') if color else ""
            root_icon = FileTypeIcons.get_icon(dir_path) if show_icons else ""
            root_name = f"{root_icon} {dir_path.name}/" if show_icons else f"{dir_path.name}/"
            root_tree = Tree(
                f"[{style}]{root_name}[/]" if style else root_name
            )
            add_tree_branch(root_tree, dir_path)
            return root_tree
        except Exception as e:
            logging.error(f"Error building tree: {str(e)}")
            return Tree("Error: Unable to build directory tree")

    @staticmethod
    def format_json_tree(dir_path: Path, scan_func, platform_handler) -> Dict[str, Any]:
        """Format directory structure as JSON"""
        try:
            scan_result = scan_func(dir_path)
            
            contents = []
            
            # Process directories
            for d in scan_result['dirs']:
                try:
                    contents.append(MapFormatter.format_json_tree(d, scan_func, platform_handler))
                except Exception as e:
                    logging.warning(f"Error processing directory {d} for JSON: {str(e)}")
                    contents.append({
                        "name": d.name,
                        "type": "directory",
                        "path": str(d),
                        "error": str(e)
                    })
            
            # Process files
            for f in scan_result['files']:
                try:
                    file_info = platform_handler.get_file_info(f)
                    contents.append({
                        "name": f.name,
                        "type": "file",
                        "path": str(f),
                        "size": file_info.get('size'),
                        "modified": file_info.get('modified').isoformat() if file_info.get('modified') else None,
                        "created": file_info.get('created').isoformat() if file_info.get('created') else None,
                        "permissions": file_info.get('permissions')
                    })
                except Exception as e:
                    logging.warning(f"Error processing file {f} for JSON: {str(e)}")
                    contents.append({
                        "name": f.name,
                        "type": "file",
                        "path": str(f),
                        "error": str(e)
                    })
            
            return {
                "name": dir_path.name,
                "type": "directory",
                "path": str(dir_path),
                "contents": contents
            }
        except Exception as e:
            logging.error(f"Error building JSON tree for {dir_path}: {str(e)}")
            return {
                "name": dir_path.name,
                "type": "directory", 
                "path": str(dir_path),
                "error": str(e)
            }

    @staticmethod
    def format_markdown_tree(
        dir_path: Path, 
        scan_func, 
        max_preview: int,
        root_preview: int,
        max_depth: Optional[int],
        show_details: bool,
        platform_handler,
        indent: int = 0,
        current_depth: int = 0
    ) -> List[str]:
        """Format directory structure as Markdown"""
        if max_depth is not None and current_depth >= max_depth:
            return []

        md_output = []
        try:
            scan_result = scan_func(dir_path)
            current_max_preview = root_preview if current_depth == 0 else max_preview

            # Add directories
            for d in scan_result['dirs'][:current_max_preview]:
                try:
                    md_output.append(f"{'  ' * indent}- 📁 {d.name}/")
                    md_output.extend(
                        MapFormatter.format_markdown_tree(
                            d, scan_func, max_preview, root_preview,
                            max_depth, show_details, platform_handler,
                            indent + 1, current_depth + 1
                        )
                    )
                except Exception as e:
                    logging.warning(f"Error processing directory {d} for Markdown: {str(e)}")
                    md_output.append(f"{'  ' * indent}- 📁 {d.name}/ (error: {str(e)})")

            if len(scan_result['dirs']) > current_max_preview:
                md_output.append(
                    f"{'  ' * indent}- 📁 (... {len(scan_result['dirs']) - current_max_preview} more folders)"
                )

            # Add files
            for f in scan_result['files'][:current_max_preview]:
                try:
                    if show_details:
                        file_info = platform_handler.get_file_info(f)
                        size = file_info.get('size', 0)
                        modified = file_info.get('modified')
                        modified_str = modified.strftime('%Y-%m-%d %H:%M:%S') if modified else 'unknown'
                        details = f" (size: {size} bytes, modified: {modified_str})"
                        md_output.append(f"{'  ' * indent}- 📄 {f.name}{details}")
                    else:
                        md_output.append(f"{'  ' * indent}- 📄 {f.name}")
                except Exception as e:
                    logging.warning(f"Error processing file {f} for Markdown: {str(e)}")
                    md_output.append(f"{'  ' * indent}- 📄 {f.name} (error: {str(e)})")

            if len(scan_result['files']) > current_max_preview:
                md_output.append(
                    f"{'  ' * indent}- 📄 (... {len(scan_result['files']) - current_max_preview} more files)"
                )

        except Exception as e:
            logging.error(f"Error building markdown tree for {dir_path}: {str(e)}")
            md_output.append(f"{'  ' * indent}- 🚫 Error: {str(e)}")

        return md_output
    
    @staticmethod
    def format_html_tree(dir_path: Path, scan_func, platform_handler) -> str:
        """Format directory structure as HTML"""
        def format_size(size: int) -> str:
            if size is None:
                return "N/A"
            return SizeFormatter.format_size(size)

        def build_tree_html(path: Path) -> str:
            try:
                scan_result = scan_func(path)
                html_parts = []
                
                # Process directories
                for d in scan_result['dirs']:
                    try:
                        icon = FileTypeIcons.get_icon(d)
                        dir_html = f"""
                            <div class="tree-item" onclick="toggleDirectory(this)">
                                <i class="fas fa-chevron-right"></i>
                                {icon}
                                <span>{d.name}</span>
                            </div>
                            <div class="tree-content hidden">
                                {build_tree_html(d)}
                            </div>
                        """
                        html_parts.append(dir_html)
                    except Exception as e:
                        logging.warning(f"Error processing directory {d} for HTML: {str(e)}")
                        continue
                
                # Process files
                for f in scan_result['files']:
                    try:
                        file_info = platform_handler.get_file_info(f)
                        size = format_size(file_info.get('size'))
                        modified = file_info.get('modified')
                        modified_str = modified.strftime('%Y-%m-%d %H:%M:%S') if modified else "N/A"
                        
                        icon = FileTypeIcons.get_icon(f)
                        file_html = f"""
                            <div class="tree-item">
                                {icon}
                                <span>{f.name}</span>
                                <span class="file-size" title="Modified: {modified_str}">{size}</span>
                            </div>
                        """
                        html_parts.append(file_html)
                    except Exception as e:
                        logging.warning(f"Error processing file {f} for HTML: {str(e)}")
                        continue
                        
                return '\n'.join(html_parts)
            except Exception as e:
                logging.error(f"Error building HTML tree for {path}: {str(e)}")
                return f"<div class='error'>Error building directory tree: {str(e)}</div>"

        try:
            return build_tree_html(dir_path)
        except Exception as e:
            logging.error(f"Error building HTML tree: {str(e)}")
            return f"<div class='error'>Error building directory tree: {str(e)}</div>"

    @staticmethod
    def format_statistics(stats: DirectoryStats) -> Table:
        """Format directory statistics as a Rich table"""
        try:
            stats_summary = stats.get_summary()
            
            table = Table(title="Directory Statistics", show_header=True)
            table.add_column("Metric", style="bold cyan")
            table.add_column("Value")
            
            table.add_row("Total Files", str(stats_summary['total_files']))
            table.add_row("Total Directories", str(stats_summary['total_dirs']))
            table.add_row("Total Size", stats_summary['total_size'])
            
            file_types = "\n".join(f"{ext or 'no ext'}: {count}" 
                                  for ext, count in list(stats_summary['file_types'].items())[:10])
            table.add_row("File Types (top 10)", file_types)
            
            largest_files = "\n".join(f"{path.split('/')[-1]}: {size}" 
                                     for path, size in stats_summary['largest_files'][:5])
            table.add_row("Largest Files (top 5)", largest_files)
            
            newest_files = "\n".join(f"{path.split('/')[-1]}: {date}" 
                                    for path, date in stats_summary['newest_files'][:5])
            table.add_row("Recently Modified (top 5)", newest_files)
            
            return table
        except Exception as e:
            logging.error(f"Error formatting statistics: {str(e)}")
            # Return basic table on error
            table = Table(title="Directory Statistics", show_header=True)
            table.add_column("Metric", style="bold cyan")
            table.add_column("Value")
            table.add_row("Error", f"Could not generate statistics: {str(e)}")
            return table


class DirectoryMapper:
    def __init__(
        self,
        path: Union[str, Path],
        max_preview: int = 3,
        root_preview: int = 5,
        show_hidden: bool = False,
        max_depth: Optional[int] = None,
        color: bool = True,
        filter_ext: Optional[List[str]] = None,
        exclude_ext: Optional[List[str]] = None,
        show_details: bool = False,
        output_format: str = "text",
        sort_by: str = "name",
        follow_symlinks: bool = False,
        log_path: Optional[str] = None,
        theme: Optional[Dict[str, Any]] = None,
        show_stats: bool = False,
        show_progress: bool = True,
        show_icons: bool = True,
    ):
        """Initialize DirectoryMapper with configuration and validation"""
        try:
            self.console = Console(color_system="auto" if color else None)
            self.platform = PlatformHandler()
            self.path = self.platform.normalize_path(path)
            
            # Validate path exists and is accessible
            if not self.path.exists():
                raise FileNotFoundError(f"Path does not exist: {path}")
            if not self.path.is_dir():
                raise ValueError(f"Path is not a directory: {path}")
            if not self.platform.check_access(self.path):
                raise PermissionError(f"No read access to path: {path}")
            
            # Validate configuration parameters
            self.max_preview = max(1, min(100, max_preview))
            self.root_preview = max(1, min(100, root_preview))
            self.show_hidden = bool(show_hidden)
            self.max_depth = max_depth if max_depth is None or max_depth > 0 else None
            self.color = bool(color)
            self.filter_ext = set(filter_ext or [])
            self.exclude_ext = set(exclude_ext or [])
            self.show_details = bool(show_details)
            
            # Validate output format
            valid_formats = ['text', 'json', 'markdown', 'html']
            self.output_format = output_format if output_format in valid_formats else 'text'
            
            # Validate sort option
            valid_sorts = ['name', 'size', 'date']
            self.sort_by = sort_by if sort_by in valid_sorts else 'name'
            
            self.follow_symlinks = bool(follow_symlinks)
            
            # Set theme with fallback
            self.theme = theme or {
                "name": "default",
                "description": "Default fallback theme",
                "directory": "bold light_green",
                "file": "bold yellow", 
                "root": "bold red",
                "details": "dim cyan",
                "more_items": "dim",
                "subdirectory_count": "dim"
            }
            
            self.show_stats = bool(show_stats)
            self.show_progress = bool(show_progress)
            self.show_icons = bool(show_icons)
            
            # Initialize optional components
            self.stats = DirectoryStats() if show_stats else None
            self.progress = ProgressTracker(self.console) if show_progress else None
            
            # Setup logging with validation
            log_file = log_path or 'dlens.log'
            try:
                logging.basicConfig(
                    filename=log_file,
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s: %(message)s',
                    filemode='a'
                )
            except (PermissionError, OSError) as e:
                logging.warning(f"Cannot write to log file {log_file}: {e}")
                # Continue without file logging
            
            # Initialize thread pool with reasonable limits
            max_threads = min(8, (self.platform.max_threads or 4))
            self.executor = None  # Initialize lazily
            self.cache = {}
            
        except Exception as e:
            logging.error(f"Failed to initialize DirectoryMapper: {e}")
            raise

    @contextmanager
    def _get_executor(self):
        """Context manager for thread pool executor"""
        if self.executor is None:
            max_threads = min(8, (self.platform.max_threads or 4))
            self.executor = ThreadPoolExecutor(max_workers=max_threads)
        
        try:
            yield self.executor
        finally:
            # Don't shutdown here, let the main cleanup handle it
            pass

    def _get_entry_sort_key(self, entry: Path) -> Any:
        """Get sorting key for directory entry"""
        try:
            if self.sort_by == "size":
                try:
                    return entry.stat().st_size
                except (PermissionError, OSError):
                    return 0
            elif self.sort_by == "date":
                try:
                    return entry.stat().st_mtime
                except (PermissionError, OSError):
                    return 0
            else:  # name
                return str(entry).lower()
        except Exception as e:
            logging.debug(f"Error getting sort key for {entry}: {e}")
            return str(entry).lower()  # Fallback to name

    def _sort_entries(self, entries: List[Path]) -> List[Path]:
        """Sort directory entries"""
        try:
            return sorted(entries, key=self._get_entry_sort_key, reverse=(self.sort_by in ["size", "date"]))
        except Exception as e:
            logging.warning(f"Error sorting entries: {e}")
            return entries  # Return unsorted on error

    def _filter_entry(self, entry: Path) -> bool:
        """Filter directory entries"""
        try:
            if not self.show_hidden and entry.name.startswith('.'):
                return False
                
            if entry.is_file():
                ext = entry.suffix.lower()
                if self.filter_ext and ext not in self.filter_ext:
                    return False
                if self.exclude_ext and ext in self.exclude_ext:
                    return False
                    
            return True
        except Exception as e:
            logging.debug(f"Error filtering entry {entry}: {str(e)}")
            return False

    def _scan_directory(self, dir_path: Path) -> Dict[str, List[Path]]:
        """Scan directory with improved error handling and memory management"""
        try:
            if not self.platform.check_access(dir_path):
                logging.warning(f"Access denied to {dir_path}")
                return {'dirs': [], 'files': []}
            
            # Use iterator to avoid loading all entries into memory at once
            dirs = []
            files = []
            processed_count = 0
            
            try:
                # Process entries one by one instead of loading all at once
                for entry in dir_path.iterdir():
                    # Limit processing to prevent memory issues
                    if processed_count > 10000:  # Reasonable limit
                        logging.warning(f"Too many entries in {dir_path}, truncating")
                        break
                    
                    if not self._filter_entry(entry):
                        continue
                    
                    try:
                        if entry.is_dir() and (self.follow_symlinks or not entry.is_symlink()):
                            dirs.append(entry)
                            if self.show_stats and self.stats:
                                self.stats.add_directory()
                        elif entry.is_file():
                            files.append(entry)
                            if self.show_stats and self.stats:
                                self.stats.add_file(entry)
                        
                        processed_count += 1
                        
                        # Update progress periodically
                        if self.show_progress and self.progress and processed_count % 100 == 0:
                            self.progress.update(100)
                            
                    except (PermissionError, OSError) as e:
                        logging.debug(f"Error processing entry {entry}: {e}")
                        continue
                        
            except PermissionError as e:
                logging.warning(f"Permission denied iterating {dir_path}: {e}")
            except OSError as e:
                logging.warning(f"OS error iterating {dir_path}: {e}")
            
            # Sort entries
            try:
                dirs = self._sort_entries(dirs)
                files = self._sort_entries(files)
            except Exception as e:
                logging.warning(f"Error sorting entries: {e}")
                # Continue with unsorted entries
            
            return {'dirs': dirs, 'files': files}
            
        except Exception as e:
            logging.error(f"Error scanning directory {dir_path}: {e}")
            return {'dirs': [], 'files': []}

    def export_text(self) -> None:
        """Export directory structure in text format with proper cleanup"""
        try:
            if self.show_progress and self.progress:
                self.progress.start()
            
            # Load icons if needed
            if self.show_icons:
                FileTypeIcons.load_icons()
            
            # Create rich tree visualization
            tree = MapFormatter.format_rich_tree(
                self.path,
                self._scan_directory,
                self.theme,
                self.max_preview,
                self.root_preview,
                self.max_depth,
                self.show_details,
                self.show_icons,
                self.color,
                self.platform
            )
            self.console.print(tree)
            
            # Show statistics if enabled
            if self.show_stats and self.stats:
                self.console.print("\n")
                stats_table = MapFormatter.format_statistics(self.stats)
                self.console.print(stats_table)
            
            # Show progress if enabled
            if self.show_progress and self.progress:
                self.console.print("\n")
                self.console.print(f"[dim]{self.progress.get_progress()}[/]")
                
        except KeyboardInterrupt:
            self.console.print("\n[red]Operation cancelled by user[/]")
            raise
        except Exception as e:
            logging.error(f"Error in text export: {e}")
            self.console.print(f"[red]Error: {e}[/]")
            raise
        finally:
            self._cleanup_resources()

    def export_json(self) -> None:
        """Export directory structure in JSON format"""
        try:
            if self.show_progress and self.progress:
                self.progress.start()
            
            output = {
                "directory_tree": MapFormatter.format_json_tree(
                    self.path,
                    self._scan_directory,
                    self.platform
                )
            }
            
            # Include statistics if enabled
            if self.show_stats and self.stats:
                try:
                    output["statistics"] = self.stats.get_summary()
                except Exception as e:
                    logging.warning(f"Error collecting statistics for JSON: {e}")
            
            # Include progress if enabled
            if self.show_progress and self.progress:
                output["scan_info"] = {
                    "progress": self.progress.get_progress(),
                    "timestamp": datetime.now().isoformat()
                }
            
            print(json.dumps(output, indent=4, default=str))
            
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            raise
        except Exception as e:
            logging.error(f"Error in JSON export: {e}")
            print(f"Error: {e}")
            raise
        finally:
            self._cleanup_resources()

    def export_markdown(self) -> None:
        """Export directory structure in Markdown format"""
        try:
            if self.show_progress and self.progress:
                self.progress.start()
            
            md_lines = MapFormatter.format_markdown_tree(
                self.path,
                self._scan_directory,
                self.max_preview,
                self.root_preview,
                self.max_depth,
                self.show_details,
                self.platform
            )
            
            # Include statistics if enabled
            if self.show_stats and self.stats:
                try:
                    stats = self.stats.get_summary()
                    md_lines.extend([
                        "\n## Directory Statistics\n",
                        f"- Total Files: {stats['total_files']}",
                        f"- Total Directories: {stats['total_dirs']}",
                        f"- Total Size: {stats['total_size']}",
                        "\n### File Types\n",
                        *[f"- {ext or 'no ext'}: {count}" 
                          for ext, count in list(stats['file_types'].items())[:10]],
                        "\n### Largest Files\n",
                        *[f"- {path}: {size}" 
                          for path, size in stats['largest_files'][:5]],
                        "\n### Recently Modified\n",
                        *[f"- {path}: {date}" 
                          for path, date in stats['newest_files'][:5]]
                    ])
                except Exception as e:
                    logging.warning(f"Error collecting statistics for Markdown: {e}")
            
            # Include progress if enabled
            if self.show_progress and self.progress:
                md_lines.append(f"\n*Scan completed: {self.progress.get_progress()}*")
            
            print("\n".join(md_lines))
            
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            raise
        except Exception as e:
            logging.error(f"Error in Markdown export: {e}")
            print(f"Error: {e}")
            raise
        finally:
            self._cleanup_resources()
            
    def export_html(self) -> None:
        """Export directory structure as interactive HTML with better error handling"""
        try:
            if self.show_progress and self.progress:
                self.progress.start()
                
            # Load required resources
            if self.show_icons:
                FileTypeIcons.load_icons()
                
            # Initialize stats if needed
            if self.show_stats and not self.stats:
                self.stats = DirectoryStats()
            
            # Get template with error handling
            try:
                template_content = ResourcesManager.get_template('directory_map.html')
                template = Template(template_content)
            except Exception as e:
                logging.error(f"Failed to load HTML template: {e}")
                raise ValueError(f"Cannot load HTML template: {e}")
            
            # Build directory tree HTML
            try:
                directory_content = MapFormatter.format_html_tree(
                    self.path,
                    self._scan_directory,
                    self.platform
                )
            except Exception as e:
                logging.error(f"Failed to build HTML tree: {e}")
                directory_content = f"<div class='error'>Error building directory tree: {e}</div>"
            
            # Get statistics summary
            if self.show_stats and self.stats:
                try:
                    stats_summary = self.stats.get_summary()
                    stats_data = {
                        'total_files': stats_summary['total_files'],
                        'total_dirs': stats_summary['total_dirs'],
                        'total_size': stats_summary['total_size'],
                        'file_types': stats_summary['file_types'],
                        'largest_files': stats_summary['largest_files'],
                        'newest_files': stats_summary['newest_files'],
                        'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                except Exception as e:
                    logging.warning(f"Error collecting statistics: {e}")
                    stats_data = self._get_empty_stats()
            else:
                stats_data = self._get_empty_stats()
            
            # Render template
            try:
                html_content = template.render(
                    directory_content=directory_content,
                    stats=stats_data,
                    root_path=str(self.path),
                    theme=self.theme
                )
            except Exception as e:
                logging.error(f"Template rendering failed: {e}")
                raise ValueError(f"Failed to render HTML template: {e}")
            
            # Write output file
            output_path = self._get_output_path('directory_map.html')
            try:
                self._write_output_file(output_path, html_content)
                print(f"Directory map exported to {output_path}")
            except Exception as e:
                logging.error(f"Failed to write HTML file: {e}")
                raise IOError(f"Cannot write to {output_path}: {e}")
                
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            raise
        except Exception as e:
            logging.error(f"Error in HTML export: {e}")
            print(f"Error: {e}")
            raise
        finally:
            self._cleanup_resources()

    def _get_empty_stats(self) -> Dict[str, Any]:
        """Get empty statistics structure"""
        return {
            'total_files': 0,
            'total_dirs': 0,
            'total_size': '0 B',
            'file_types': {},
            'largest_files': [],
            'newest_files': [],
            'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def _get_output_path(self, default_name: str) -> Path:
        """Get validated output path"""
        if hasattr(self, 'output_file') and self.output_file:
            output_path = Path(self.output_file)
        else:
            output_path = Path(default_name)
            
        # Make absolute path
        if not output_path.is_absolute():
            output_path = Path.cwd() / output_path
            
        # Create parent directories
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            logging.error(f"Cannot create output directory: {e}")
            raise
            
        return output_path

    def _write_output_file(self, output_path: Path, content: str) -> None:
        """Write content to file with atomic operation"""
        temp_path = output_path.with_suffix(output_path.suffix + '.tmp')
        
        try:
            # Atomic write - write to temp file first
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
                f.flush()  # Ensure data is written
                os.fsync(f.fileno())  # Force OS to write to disk
                
            # Move temp file to final location
            temp_path.replace(output_path)
            
        except Exception as e:
            # Clean up temp file if it exists
            try:
                if temp_path.exists():
                    temp_path.unlink()
            except Exception:
                pass
            raise

    def _cleanup_resources(self) -> None:
        """Clean up all resources properly"""
        try:
            if self.executor:
                self.executor.shutdown(wait=True)
                self.executor = None
        except Exception as e:
            logging.error(f"Error shutting down executor: {e}")
        
        # Clear cache to free memory
        self.cache.clear()

    def export(self) -> None:
        """Main export method with comprehensive error handling"""
        try:
            if self.output_format == "text":
                self.export_text()
            elif self.output_format == "json":
                self.export_json()
            elif self.output_format == "markdown":
                self.export_markdown()
            elif self.output_format == "html":
                self.export_html()
            else:
                raise ValueError(f"Unsupported output format: {self.output_format}")
                
        except KeyboardInterrupt:
            logging.info("Export cancelled by user")
            raise
        except Exception as e:
            logging.error(f"Export failed: {e}")
            raise
        finally:
            self._cleanup_resources()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self._cleanup_resources()

    def __del__(self):
        """Cleanup resources on deletion"""
        try:
            self._cleanup_resources()
        except Exception:
            # Don't raise exceptions in __del__
            pass