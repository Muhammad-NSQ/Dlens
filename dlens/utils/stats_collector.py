from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from dlens.utils.size_formatter import SizeFormatter

class DirectoryStats:
    """Collect and analyze directory statistics"""
    
    def __init__(self):
        self.total_files = 0
        self.total_dirs = 0
        self.total_size = 0
        self.file_types = {}
        self.largest_files = []
        self.newest_files = []
        
    def add_file(self, file_path: Path):
        """Process a file for statistics"""
        try:
            stat = file_path.stat()
            self.total_files += 1
            self.total_size += stat.st_size
            
            # Track file types
            ext = file_path.suffix.lower()
            self.file_types[ext] = self.file_types.get(ext, 0) + 1
            
            # Track largest files (keep top 10)
            self.largest_files.append((file_path, stat.st_size))
            self.largest_files.sort(key=lambda x: x[1], reverse=True)
            self.largest_files = self.largest_files[:10]
            
            # Track newest files (keep top 10)
            self.newest_files.append((file_path, stat.st_mtime))
            self.newest_files.sort(key=lambda x: x[1], reverse=True)
            self.newest_files = self.newest_files[:10]
            
        except Exception:
            pass
            
    def add_directory(self):
        """Count directories"""
        self.total_dirs += 1
        
    def get_summary(self) -> Dict[str, Any]:
        """Get statistical summary"""
        return {
            'total_files': self.total_files,
            'total_dirs': self.total_dirs,
            'total_size': SizeFormatter.format_size(self.total_size),
            'file_types': dict(sorted(self.file_types.items(), key=lambda x: x[1], reverse=True)),
            'largest_files': [(str(p), SizeFormatter.format_size(s)) for p, s in self.largest_files],
            'newest_files': [(str(p), datetime.fromtimestamp(t).strftime('%Y-%m-%d %H:%M:%S')) 
                           for p, t in self.newest_files]
        }