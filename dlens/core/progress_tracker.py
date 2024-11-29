from datetime import datetime
from rich.console import Console
from datetime import datetime

class ProgressTracker:
    """Track and display progress for large directory scans"""
    
    def __init__(self, console: Console):
        self.console = console
        self.total_items = 0
        self.processed_items = 0
        self.start_time = None
        
    def start(self):
        """Start progress tracking"""
        self.start_time = datetime.now()
        
    def update(self, items_found: int = 1):
        """Update progress count"""
        self.processed_items += items_found
        
    def get_progress(self) -> str:
        """Get progress status message"""
        elapsed = datetime.now() - self.start_time
        items_per_sec = self.processed_items / elapsed.total_seconds() if elapsed.total_seconds() > 0 else 0
        return f"Processed {self.processed_items:,} items ({items_per_sec:.1f} items/sec)"