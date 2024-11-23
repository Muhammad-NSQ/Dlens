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
        log_path: Optional[str] = None,
        theme: Optional[Dict[str, Any]] = None  # Add theme parameter
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
        self.theme = theme or {}  # Initialize theme
        
        # Setup console and logging
        self.console = Console(color_system="auto" if color else None)
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
        """Build a rich tree representation with proper theme application"""
        def add_tree_branch(parent: Tree, dir_path: Path, level: int = 0) -> None:
            if self.max_depth is not None and level >= self.max_depth:
                return

            scan_result = self._scan_directory(dir_path)
            dirs = scan_result['dirs']
            files = scan_result['files']

            current_max_preview = self.root_preview if level == 0 else self.max_preview

            # Add directories with theme
            for d in dirs[:current_max_preview]:
                try:
                    # Get directory style from theme
                    dir_style = self.theme.get('colors', {}).get('directory', "bold light_green")
                    subtree = parent.add(f"[{dir_style}]{d.name}/[/]")
                    add_tree_branch(subtree, d, level + 1)
                except Exception as e:
                    logging.warning(f"Error adding directory {d}: {str(e)}")

            if len(dirs) > current_max_preview:
                count_style = self.theme.get('colors', {}).get('subdirectory_count', "dim")
                parent.add(
                    f"[{count_style}](... {len(dirs) - current_max_preview} more folders)[/]"
                )

            # Add files with theme
            for f in files[:current_max_preview]:
                try:
                    file_style = self.theme.get('colors', {}).get('file', "bold yellow")
                    if self.show_details:
                        file_info = self.platform.get_file_info(f)
                        details = (
                            f" (size: {file_info['size']} bytes, "
                            f"modified: {file_info['modified'].strftime('%Y-%m-%d %H:%M:%S')})"
                        )
                        display_name = f"{f.name}{details}"
                    else:
                        display_name = f.name

                    parent.add(f"[{file_style}]{display_name}[/]")
                except Exception as e:
                    logging.warning(f"Error adding file {f}: {str(e)}")

            if len(files) > current_max_preview:
                count_style = self.theme.get('colors', {}).get('subdirectory_count', "dim")
                parent.add(
                    f"[{count_style}](... {len(files) - current_max_preview} more files)[/]"
                )

        try:
            # Get root style from theme
            root_style = self.theme.get('colors', {}).get('root', "bold red")
            root_tree = Tree(f"[{root_style}]{self.path.name}/[/]")
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
        
class ThemeManager:
    """Advanced theme management for directory mapping"""
    
    def __init__(self, theme_path: Optional[str] = None):
        """
        Initialize theme manager with theme selection and loading
        
        Args:
            theme_path: Path to custom theme file or theme name
        """
        self.default_config_dir = self._get_config_directory()
        self.themes_path = os.path.join(self.default_config_dir, 'themes.json')
        self.default_theme_path = os.path.join(self.default_config_dir, 'default_theme.json')
        
        # Ensure themes file exists with default themes
        self._initialize_themes_file()
        
        # Determine theme to use
        self.themes = self._load_themes()
        self.theme = self._select_theme(theme_path)

    def _get_config_directory(self) -> str:
        """
        Get or create a configuration directory for Dlens
        
        Returns:
            Path to configuration directory
        """
        config_home = os.path.expanduser('~/.config/dlens')
        os.makedirs(config_home, exist_ok=True)
        return config_home

    def _initialize_themes_file(self):
        """
        Create default themes.json if it doesn't exist
        """
        default_themes = {
            "themes": [
                {
                    "name": "default",
                    "description": "Classic color scheme with green directories and yellow files",
                    "colors": {
                        "directory": "bold light_green",
                        "file": "bold yellow",
                        "root": "bold red",
                        "subdirectory_count": "dim"
                    }
                },
                {
                    "name": "ocean",
                    "description": "Calming blue-based color palette",
                    "colors": {
                        "directory": "bold cyan",
                        "file": "bold blue",
                        "root": "bold bright_blue",
                        "subdirectory_count": "dim"
                    }
                },
                {
                    "name": "forest",
                    "description": "Natural green and brown earth tones",
                    "colors": {
                        "directory": "bold green",
                        "file": "bold dark_green",
                        "root": "bold bright_green",
                        "subdirectory_count": "italic dim"
                    }
                },
                {
                    "name": "pastel",
                    "description": "Soft, muted color palette",
                    "colors": {
                        "directory": "bold magenta",
                        "file": "bold light_magenta",
                        "root": "bold bright_magenta",
                        "subdirectory_count": "dim"
                    }
                },
                {
                    "name": "monochrome",
                    "description": "Clean, minimalist black and white theme",
                    "colors": {
                        "directory": "bold white",
                        "file": "dim white",
                        "root": "bold bright_white",
                        "subdirectory_count": "dim"
                    }
                }
            ]
        }
        
        if not os.path.exists(self.themes_path):
            with open(self.themes_path, 'w') as f:
                json.dump(default_themes, f, indent=4)

    def _load_themes(self) -> Dict[str, Dict[str, Any]]:
        """
        Load themes from external JSON file
        
        Returns:
            Dictionary of themes
        """
        try:
            with open(self.themes_path, 'r') as f:
                themes_data = json.load(f)
                return {theme['name']: theme for theme in themes_data.get('themes', [])}
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logging.error(f"Error loading themes: {e}")
            return {}

    def _select_theme(self, theme_input: Optional[str] = None) -> Dict[str, Any]:
        """
        Select and load a theme based on input with better error handling
        
        Args:
            theme_input: Theme name or path to theme file
        
        Returns:
            Selected theme dictionary
        """
        # Set default theme structure
        default_theme = {
            "name": "default",
            "colors": {
                "directory": "bold light_green",
                "file": "bold yellow",
                "root": "bold red",
                "subdirectory_count": "dim"
            }
        }

        # If no theme specified, return default
        if not theme_input:
            if os.path.exists(self.default_theme_path):
                try:
                    with open(self.default_theme_path, 'r') as f:
                        default_theme_config = json.load(f)
                        theme_name = default_theme_config.get('theme', 'default')
                        return self.themes.get(theme_name, default_theme)
                except (json.JSONDecodeError, FileNotFoundError):
                    return default_theme
            return default_theme

        # Try to load specified theme
        if theme_input in self.themes:
            return self.themes[theme_input]
        
        # Try loading from file
        try:
            if os.path.exists(theme_input):
                return self._load_theme_from_file(theme_input)
        except Exception as e:
            logging.warning(f"Could not load theme '{theme_input}': {e}")
        
        # Return default theme if all else fails
        return default_theme

    def _load_theme_from_file(self, theme_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load theme from JSON or YAML file
        
        Args:
            theme_path: Path to theme configuration file
        
        Returns:
            Loaded theme dictionary
        """
        path = Path(theme_path)
        
        try:
            with open(path, 'r') as f:
                theme_data = json.load(f)
                
                # Validate theme structure
                if not isinstance(theme_data, dict) or 'colors' not in theme_data:
                    raise ValueError("Invalid theme format")
                
                # Merge with default theme, allowing partial overrides
                default_theme = self.themes.get('default', {})
                return {
                    "name": theme_data.get('name', 'custom'),
                    "description": theme_data.get('description', 'Custom theme'),
                    "colors": {**default_theme.get('colors', {}), **theme_data.get('colors', {})}
                }
        except (json.JSONDecodeError) as e:
            raise ValueError(f"Error parsing theme file: {e}")
        except FileNotFoundError:
            raise ValueError(f"Theme file not found: {theme_path}")

    def set_default_theme(self, theme_name: str):
        """
        Set a default theme for future uses
        
        Args:
            theme_name: Name of the theme to set as default
        """
        if theme_name not in self.themes:
            raise ValueError(f"Theme '{theme_name}' not found in themes")
        
        # Save default theme configuration
        with open(self.default_theme_path, 'w') as f:
            json.dump({"theme": theme_name}, f)
        
        logging.info(f"Default theme set to '{theme_name}'")

    def list_themes(self) -> List[Dict[str, str]]:
        """
        List available themes with their descriptions
        
        Returns:
            List of theme information dictionaries
        """
        return [
            {
                "name": name, 
                "description": theme.get("description", "No description")
            } 
            for name, theme in self.themes.items()
        ]

    def add_theme(self, theme: Dict[str, Any]):
        """
        Add a new theme to the themes file
        
        Args:
            theme: Theme configuration dictionary
        """
        # Validate theme structure
        if not isinstance(theme, dict) or 'name' not in theme or 'colors' not in theme:
            raise ValueError("Invalid theme structure")
        
        # Load existing themes
        with open(self.themes_path, 'r') as f:
            themes_data = json.load(f)
        
        # Check if theme already exists
        existing_theme = [t for t in themes_data['themes'] if t['name'] == theme['name']]
        
        if existing_theme:
            # Update existing theme
            index = themes_data['themes'].index(existing_theme[0])
            themes_data['themes'][index] = theme
        else:
            # Add new theme
            themes_data['themes'].append(theme)
        
        # Write back to file
        with open(self.themes_path, 'w') as f:
            json.dump(themes_data, f, indent=4)
        
        # Reload themes
        self.themes = self._load_themes()

    def get_style(self, element_type: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get style for a specific element type
        
        Args:
            element_type: Type of element (directory, file, root, etc.)
            default: Fallback style if not defined in theme
        
        Returns:
            Styled string or None
        """
        return self.theme['colors'].get(element_type, default)

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
    parser.add_argument(
        "--theme", 
        help="Theme name or path to custom theme file"
    )
    parser.add_argument(
        "--set-default-theme", 
        help="Set a theme as the default for future uses"
    )
    parser.add_argument(
        "--list-themes", 
        action="store_true",
        help="List available predefined themes"
    )
    parser.add_argument(
        "--add-theme", 
        type=str,
        help="Path to a new theme JSON file to add to themes"
    )

    args = parser.parse_args()
    
    # Initialize theme manager
    theme_manager = ThemeManager()
    
    # Handle theme-related actions
    if args.set_default_theme:
        try:
            theme_manager.set_default_theme(args.set_default_theme)
            print(f"Default theme set to '{args.set_default_theme}'")
            return
        except ValueError as e:
            print(f"Error: {e}")
            return

    if args.list_themes:
        print("Available Themes:")
        for theme in theme_manager.list_themes():
            print(f"- {theme['name']}: {theme['description']}")
        return

    if args.add_theme:
        try:
            with open(args.add_theme, 'r') as f:
                new_theme = json.load(f)
            theme_manager.add_theme(new_theme)
            print(f"Theme '{new_theme['name']}' added successfully.")
            return
        except Exception as e:
            print(f"Error adding theme: {e}")
            return

    # Get theme configuration if specified
    theme = None
    if args.theme:
        theme = theme_manager._select_theme(args.theme)

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
        log_path=args.log,
        theme=theme
    )
    
    mapper.export()

if __name__ == "__main__":
    main()