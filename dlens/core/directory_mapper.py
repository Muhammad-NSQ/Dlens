import json
import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Union

from rich.console import Console
from rich.tree import Tree

from datetime import datetime

from rich.table import Table
from pathlib import Path

from dlens.core.platform_handler import PlatformHandler
from dlens.core.progress_tracker import ProgressTracker
from dlens.utils.stats_collector import DirectoryStats
from dlens.ui.file_icons import FileTypeIcons
from dlens.utils.size_formatter import SizeFormatter



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
        show_stats: bool = False,  # New parameter
        show_progress: bool = True,  # New parameter
        show_icons: bool = True,  # New parameter
    ):
        """
        Cross-platform directory mapping and visualization tool
        
        Args:
            path: Root directory to map 
            max_preview: Max items per subdirectory
            root_preview: Max items in root directory
            show_hidden: Include hidden files/directories
            max_depth: Maximum recursion depth
            color: Enable colored output
            filter_ext: Include only files with these extensions
            exclude_ext: Exclude files with these extensions
            show_details: Display additional file metadata
            output_format: Output style (text/json/markdown)
            sort_by: Sort entries by name/size/date
            follow_symlinks: Traverse symbolic links
            log_path: Optional logging destination
            theme: Optional theme configuration
        """
        # Setup console first
        self.console = Console(color_system="auto" if color else None)
        
        self.platform = PlatformHandler()
        self.path = self.platform.normalize_path(path)
        
        # Configuration parameters
        self.max_preview = max_preview
        self.root_preview = root_preview
        self.show_hidden = show_hidden
        self.max_depth = max_depth
        self.color = color
        self.filter_ext = set(filter_ext or [])
        self.exclude_ext = set(exclude_ext or [])
        self.show_details = show_details
        self.output_format = output_format
        self.sort_by = sort_by
        self.follow_symlinks = follow_symlinks
        self.theme = theme or {}
        
        # New configuration parameters
        self.show_stats = show_stats
        self.show_progress = show_progress
        self.show_icons = show_icons
        
        # Initialize components based on settings
        self.stats = DirectoryStats() if show_stats else None
        self.progress = ProgressTracker(self.console) if show_progress else None
        self.file_icons = FileTypeIcons() if show_icons else None
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
        
        # Setup logging
        logging.basicConfig(
            filename=log_path or 'Dlens.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s: %(message)s'
        )
        
        self.executor = ThreadPoolExecutor(max_workers=self.platform.max_threads)
        
        # Initialize cache
        self.cache = {}

        
    def _get_entry_sort_key(self, entry: Path) -> Any:
        """Get sorting key for directory entry with caching"""
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

    def _sort_entries(self, entries: List[Path]) -> List[Path]:
        """Sort directory entries based on selected criteria"""
        return sorted(entries, key=self._get_entry_sort_key, reverse=(self.sort_by in ["size", "date"]))

    def _filter_entry(self, entry: Path) -> bool:
        """Filter directory entries based on configuration"""
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
            logging.warning(f"Error filtering entry {entry}: {str(e)}")
            return False

    def _scan_directory(self, dir_path: Path) -> Dict[str, List[Path]]:
        """Enhanced directory scanning with progress tracking and statistics"""
        try:
            if not self.platform.check_access(dir_path):
                raise PermissionError(f"Access denied to {dir_path}")
                
            entries = list(dir_path.iterdir())
            
            # Only update progress if enabled
            if self.show_progress and self.progress:
                self.progress.update(len(entries))
            
            dirs = []
            files = []
            
            for entry in entries:
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
                except Exception as e:
                    logging.warning(f"Error processing entry {entry}: {str(e)}")
                    
            return {
                'dirs': self._sort_entries(dirs),
                'files': self._sort_entries(files)
            }
        except Exception as e:
            logging.error(f"Error scanning directory {dir_path}: {str(e)}")
            return {'dirs': [], 'files': []}

    def _build_rich_tree(self) -> Tree:
        """Build a rich tree representation with enhanced features"""
        def add_tree_branch(parent: Tree, dir_path: Path, level: int = 0) -> None:
            if self.max_depth is not None and level >= self.max_depth:
                return

            scan_result = self._scan_directory(dir_path)
            dirs = scan_result['dirs']
            files = scan_result['files']

            current_max_preview = self.root_preview if level == 0 else self.max_preview

            # Add directories
            for d in dirs[:current_max_preview]:
                try:
                    style = self.theme.get('directory', 'bold light_green') if self.color else ""
                    icon = FileTypeIcons.get_icon(d) if self.show_icons else ""
                    name = f"{icon} {d.name}/" if self.show_icons else f"{d.name}/"
                    subtree = parent.add(f"[{style}]{name}[/]" if style else name)
                    add_tree_branch(subtree, d, level + 1)
                except Exception as e:
                    logging.warning(f"Error adding directory {d}: {str(e)}")

            if len(dirs) > current_max_preview:
                more_style = self.theme.get('more_items', 'dim')
                parent.add(
                    f"[{more_style}](... {len(dirs) - current_max_preview} more folders)[/]"
                    if self.color else
                    f"(... {len(dirs) - current_max_preview} more folders)"
                )

            # Add files
            for f in files[:current_max_preview]:
                try:
                    if self.show_details:
                        file_info = self.platform.get_file_info(f)
                        size = SizeFormatter.format_size(file_info['size'])
                        details = (
                            f" [italic {self.theme.get('details', 'dim cyan')}]"
                            f"(size: {size}, "
                            f"modified: {file_info['modified'].strftime('%Y-%m-%d %H:%M:%S')})[/]"
                            if self.color else
                            f" (size: {size}, modified: {file_info['modified'].strftime('%Y-%m-%d %H:%M:%S')})"
                        )
                        icon = FileTypeIcons.get_icon(f) if self.show_icons else ""
                        display_name = f"{icon} {f.name}{details}" if self.show_icons else f"{f.name}{details}"
                    else:
                        icon = FileTypeIcons.get_icon(f) if self.show_icons else ""
                        display_name = f"{icon} {f.name}" if self.show_icons else f"{f.name}"

                    style = self.theme.get('file', 'bold yellow') if self.color else ""
                    parent.add(f"[{style}]{display_name}[/]" if style else display_name)
                except Exception as e:
                    logging.warning(f"Error adding file {f}: {str(e)}")

            if len(files) > current_max_preview:
                more_style = self.theme.get('more_items', 'dim')
                parent.add(
                    f"[{more_style}](... {len(files) - current_max_preview} more files)[/]"
                    if self.color else
                    f"(... {len(files) - current_max_preview} more files)"
                )

        try:
            style = self.theme.get('root', 'bold red') if self.color else ""
            root_icon = FileTypeIcons.get_icon(self.path) if self.show_icons else ""
            root_name = f"{root_icon} {self.path.name}/" if self.show_icons else f"{self.path.name}/"
            root_tree = Tree(
                f"[{style}]{root_name}[/]" if style else root_name
            )
            add_tree_branch(root_tree, self.path)
            return root_tree
        except Exception as e:
            logging.error(f"Error building tree: {str(e)}")
            return Tree("Error: Unable to build directory tree")
        
    def _display_statistics(self):
        """Display collected directory statistics"""
        stats = self.stats.get_summary()
        
        # Create statistics table
        table = Table(title="Directory Statistics", show_header=True)
        table.add_column("Metric", style="bold cyan")
        table.add_column("Value")
        
        # Add basic stats
        table.add_row("Total Files", str(stats['total_files']))
        table.add_row("Total Directories", str(stats['total_dirs']))
        table.add_row("Total Size", stats['total_size'])
        
        # Add file type distribution
        file_types = "\n".join(f"{ext or 'no ext'}: {count}" 
                              for ext, count in list(stats['file_types'].items())[:10])
        table.add_row("File Types (top 10)", file_types)
        
        # Add largest files
        largest_files = "\n".join(f"{path.split('/')[-1]}: {size}" 
                                 for path, size in stats['largest_files'][:5])
        table.add_row("Largest Files (top 5)", largest_files)
        
        # Add newest files
        newest_files = "\n".join(f"{path.split('/')[-1]}: {date}" 
                                for path, date in stats['newest_files'][:5])
        table.add_row("Recently Modified (top 5)", newest_files)
        
        return table

    def _build_json_tree(self, dir_path: Path) -> Dict[str, Any]:
        """Generate a detailed JSON representation of the directory"""
        try:
            scan_result = self._scan_directory(dir_path)
            
            return {
                "name": dir_path.name,
                "type": "directory",
                "path": str(dir_path),
                "contents": [
                    self._build_json_tree(d) for d in scan_result['dirs']
                ] + [
                    {
                        "name": f.name,
                        "type": "file",
                        "path": str(f),
                        **self.platform.get_file_info(f)
                    } for f in scan_result['files']
                ]
            }
        except Exception as e:
            logging.error(f"Error building JSON tree for {dir_path}: {str(e)}")
            return {"name": dir_path.name, "error": str(e)}

    def _build_markdown_tree(self, dir_path: Path, indent: int = 0, current_depth: int = 0) -> List[str]:
        """Generate a Markdown representation of the directory"""
        if self.max_depth is not None and current_depth >= self.max_depth:
            return []

        md_output = []
        try:
            scan_result = self._scan_directory(dir_path)
            max_preview = self.root_preview if current_depth == 0 else self.max_preview

            # Add directories
            for d in scan_result['dirs'][:max_preview]:
                md_output.append(f"{'  ' * indent}- 📁 {d.name}/")
                md_output.extend(
                    self._build_markdown_tree(d, indent + 1, current_depth + 1)
                )

            if len(scan_result['dirs']) > max_preview:
                md_output.append(
                    f"{'  ' * indent}- 📁 (... {len(scan_result['dirs']) - max_preview} more folders)"
                )

            # Add files
            for f in scan_result['files'][:max_preview]:
                if self.show_details:
                    file_info = self.platform.get_file_info(f)
                    details = (
                        f" (size: {file_info['size']} bytes, "
                        f"modified: {file_info['modified'].strftime('%Y-%m-%d %H:%M:%S')})"
                    )
                    md_output.append(f"{'  ' * indent}- 📄 {f.name}{details}")
                else:
                    md_output.append(f"{'  ' * indent}- 📄 {f.name}")

            if len(scan_result['files']) > max_preview:
                md_output.append(
                    f"{'  ' * indent}- 📄 (... {len(scan_result['files']) - max_preview} more files)"
                )

        except Exception as e:
            logging.error(f"Error building markdown tree for {dir_path}: {str(e)}")
            md_output.append(f"{'  ' * indent}- 🚫 Error: {str(e)}")

        return md_output

    def export(self) -> None:
        """Export directory structure with statistics"""
        try:
            # Start progress tracking if enabled
            if self.show_progress and self.progress:
                self.progress.start()
            
            # Create the main output
            if self.output_format == "text":
                # Create a layout with tree and statistics
                self.console.print(self._build_rich_tree())
                
                # Only show statistics if enabled
                if self.show_stats and self.stats:
                    self.console.print("\n")
                    self.console.print(self._display_statistics())
                
                # Only show progress if enabled
                if self.show_progress and self.progress:
                    self.console.print("\n")
                    self.console.print(f"[dim]{self.progress.get_progress()}[/]")
                
            elif self.output_format == "json":
                output = {
                    "directory_tree": self._build_json_tree(self.path)
                }
                
                # Only include statistics if enabled
                if self.show_stats and self.stats:
                    output["statistics"] = self.stats.get_summary()
                
                # Only include progress if enabled
                if self.show_progress and self.progress:
                    output["scan_info"] = {
                        "progress": self.progress.get_progress(),
                        "timestamp": datetime.now().isoformat()
                    }
                
                print(json.dumps(output, indent=4, default=str))
                
            elif self.output_format == "markdown":
                md_lines = self._build_markdown_tree(self.path)
                
                # Only include statistics if enabled
                if self.show_stats and self.stats:
                    md_lines.append("\n## Directory Statistics\n")
                    stats = self.stats.get_summary()
                    md_lines.extend([
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
                
                # Only include progress if enabled
                if self.show_progress and self.progress:
                    md_lines.append(f"\n*Scan completed: {self.progress.get_progress()}*")
                
                print("\n".join(md_lines))
                
        except Exception as e:
            logging.error(f"Export failed: {e}")
            print(f"Error: {e}")


    def __del__(self):
        """Cleanup resources"""
        try:
            self.executor.shutdown(wait=False)
        except Exception:
            pass