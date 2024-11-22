import os
import argparse
import json
import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, Union

from rich.console import Console
from rich.tree import Tree

class PlatformHandler:
    """Cross-platform directory access and information handler"""
    
    def __init__(self):
        self.is_windows = os.name == 'nt'
        self.is_macos = False if self.is_windows else os.uname().sysname == 'Darwin'
        self._setup_platform_specifics()

    def _setup_platform_specifics(self):
        """Configure platform-specific thread and performance settings"""
        try:
            if self.is_windows:
                # Safely handle Windows-specific DPI settings
                from ctypes import windll, c_uint64
                try:
                    windll.kernel32.SetProcessDpiAwarenessContext(c_uint64(-4))
                except Exception:
                    pass
                self.max_threads = min(32, os.cpu_count() * 2)
            else:
                self.max_threads = min(64, os.cpu_count() * 4)
        except ImportError:
            # Fallback if Windows libraries are unavailable
            self.max_threads = min(32, os.cpu_count() * 2)

    def normalize_path(self, path: Union[str, Path]) -> Path:
        """Normalize path for cross-platform compatibility"""
        path = Path(path).resolve()
        return Path(f'\\\\?\\{path}') if self.is_windows and len(str(path)) > 260 else path

    def check_access(self, path: Path) -> bool:
        """Check path accessibility across platforms"""
        try:
            return os.access(path, os.R_OK)
        except Exception:
            return False

    def get_file_info(self, path: Path) -> Dict[str, Any]:
        """Retrieve cross-platform file metadata"""
        try:
            stat = path.stat()
            return {
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'created': datetime.fromtimestamp(stat.st_ctime),
                'permissions': oct(stat.st_mode)[-3:] if not self.is_windows else None
            }
        except Exception as e:
            logging.warning(f"Could not retrieve file info: {e}")
            return {}

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
        log_path: Optional[str] = None
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
        """
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
        
        # Setup console and logging
        self.console = Console(color_system="auto" if color else None)
        logging.basicConfig(
            filename=log_path or 'directory_mapper.log',
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
        """Scan directory with error handling and filtering"""
        try:
            if not self.platform.check_access(dir_path):
                raise PermissionError(f"Access denied to {dir_path}")
                
            entries = list(dir_path.iterdir())
            
            dirs = []
            files = []
            
            for entry in entries:
                if not self._filter_entry(entry):
                    continue
                    
                try:
                    if entry.is_dir() and (self.follow_symlinks or not entry.is_symlink()):
                        dirs.append(entry)
                    elif entry.is_file():
                        files.append(entry)
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
                    style = "bold light_green" if self.color else ""
                    subtree = parent.add(f"[{style}]{d.name}/[/]" if style else f"{d.name}/")
                    add_tree_branch(subtree, d, level + 1)
                except Exception as e:
                    logging.warning(f"Error adding directory {d}: {str(e)}")

            if len(dirs) > current_max_preview:
                parent.add(
                    f"[dim](... {len(dirs) - current_max_preview} more folders)[/]"
                    if self.color else
                    f"(... {len(dirs) - current_max_preview} more folders)"
                )

            # Add files
            for f in files[:current_max_preview]:
                try:
                    if self.show_details:
                        file_info = self.platform.get_file_info(f)
                        details = (
                            f" (size: {file_info['size']} bytes, "
                            f"modified: {file_info['modified'].strftime('%Y-%m-%d %H:%M:%S')})"
                        )
                        display_name = f"{f.name}{details}"
                    else:
                        display_name = f.name

                    style = "bold yellow" if self.color else ""
                    parent.add(f"[{style}]{display_name}[/]" if style else display_name)
                except Exception as e:
                    logging.warning(f"Error adding file {f}: {str(e)}")

            if len(files) > current_max_preview:
                parent.add(
                    f"[dim](... {len(files) - current_max_preview} more files)[/]"
                    if self.color else
                    f"(... {len(files) - current_max_preview} more files)"
                )

        try:
            style = "bold red" if self.color else ""
            root_tree = Tree(
                f"[{style}]{self.path.name}/[/]" if style else f"{self.path.name}/"
            )
            add_tree_branch(root_tree, self.path)
            return root_tree
        except Exception as e:
            logging.error(f"Error building tree: {str(e)}")
            return Tree("Error: Unable to build directory tree")

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
        """Export directory structure in specified format"""
        try:
            if self.output_format == "text":
                self.console.print(self._build_rich_tree())
            elif self.output_format == "json":
                print(json.dumps(self._build_json_tree(self.path), indent=4, default=str))
            elif self.output_format == "markdown":
                print("\n".join(self._build_markdown_tree(self.path)))
        except Exception as e:
            logging.error(f"Export failed: {e}")
            print(f"Error: {e}")

    def __del__(self):
        """Cleanup resources"""
        try:
            self.executor.shutdown(wait=False)
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(description="Enhanced Directory Mapping Tool")
    parser.add_argument(
        "path", 
        nargs="?", 
        default=os.getcwd(), 
        help="The root directory path (default: current directory)"
    )
    parser.add_argument(
        "--max-preview", 
        type=int, 
        default=3, 
        help="Maximum number of items to preview per directory"
    )
    parser.add_argument(
        "--root-preview", 
        type=int, 
        default=5, 
        help="Maximum items to preview for the root directory"
    )
    parser.add_argument(
        "--depth", 
        type=int, 
        default=None, 
        help="Maximum depth to display"
    )
    parser.add_argument(
        "--show-hidden", 
        action="store_true", 
        help="Include hidden files and directories"
    )
    parser.add_argument(
        "--filter", 
        nargs="*", 
        help="Filter files by extensions, e.g., --filter .py .txt"
    )
    parser.add_argument(
        "--exclude", 
        nargs="*", 
        help="Exclude files by extensions, e.g., --exclude .log"
    )
    parser.add_argument(
        "--show-details", 
        action="store_true", 
        help="Show file sizes and modification dates"
    )
    parser.add_argument(
        "--output-format", 
        choices=["text", "json", "markdown"], 
        default="text", 
        help="Output format"
    )
    parser.add_argument(
        "--no-color", 
        action="store_true", 
        help="Disable color output"
    )
    parser.add_argument(
        "--sort", 
        choices=["name", "size", "date"], 
        default="name", 
        help="Sort entries by name, size, or date"
    )
    parser.add_argument(
        "--follow-symlinks", 
        action="store_true", 
        help="Follow symbolic links"
    )
    parser.add_argument(
        "--log", 
        help="Path to log file for tracking errors and access issues"
    )

    args = parser.parse_args()

    mapper = DirectoryMapper(
        path=args.path,
        max_preview=args.max_preview,
        root_preview=args.root_preview,
        max_depth=args.depth,
        show_hidden=args.show_hidden,
        filter_ext=args.filter,
        exclude_ext=args.exclude,
        show_details=args.show_details,
        color=not args.no_color,
        output_format=args.output_format,
        sort_by=args.sort,
        follow_symlinks=args.follow_symlinks,
        log_path=args.log
    )
    
    mapper.export()

if __name__ == "__main__":
    main()