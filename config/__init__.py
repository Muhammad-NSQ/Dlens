"""
Directory Lens - A cross-platform directory mapping and visualization tool
"""
from .core.directory_mapper import DirectoryMapper
from .core.platform_handler import PlatformHandler
from .core.progress_tracker import ProgressTracker
from .utils.size_formatter import SizeFormatter
from .utils.stats_collector import DirectoryStats
from .ui.theme_manager import ThemeManager
from .ui.file_icons import FileTypeIcons

__version__ = "1.0.0"
__all__ = [
    'DirectoryMapper',
    'PlatformHandler',
    'ProgressTracker',
    'SizeFormatter',
    'DirectoryStats',
    'ThemeManager',
    'FileTypeIcons'
]