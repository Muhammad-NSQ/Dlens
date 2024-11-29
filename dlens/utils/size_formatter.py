class SizeFormatter:
    """Format file sizes in human-readable format"""
    
    UNITS = ['B', 'KB', 'MB', 'GB', 'TB']
    
    @staticmethod
    def format_size(size_in_bytes: int) -> str:
        """Convert bytes to human readable format"""
        if size_in_bytes == 0:
            return "0B"
            
        size_index = 0
        size_float = float(size_in_bytes)
        
        while size_float >= 1024 and size_index < len(SizeFormatter.UNITS) - 1:
            size_float /= 1024
            size_index += 1
            
        return f"{size_float:.1f}{SizeFormatter.UNITS[size_index]}"