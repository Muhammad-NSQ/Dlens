import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Union

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