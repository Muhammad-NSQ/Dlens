"""
Directory Lens - A cross-platform directory mapping and visualization tool
"""
from dlens.core.platform_handler import PlatformHandler
from dlens.core.progress_tracker import ProgressTracker
from dlens.utils.size_formatter import SizeFormatter
from dlens.utils.stats_collector import DirectoryStats
from dlens.ui.theme_manager import ThemeManager
from dlens.ui.file_icons import FileTypeIcons

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