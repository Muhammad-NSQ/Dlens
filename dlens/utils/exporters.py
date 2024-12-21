import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from jinja2 import Environment
import os
from urllib.parse import quote

from dlens.core.search_handler import SearchResult
from dlens.ui.file_icons import FileTypeIcons
from dlens.resources.resources_manager import ResourcesManager


class SearchExporter:
    """Handles exporting search results in various formats"""
    
    def __init__(self, results: List[SearchResult]):
        self.results = results
        self._ensure_icons_loaded()
    
    def _ensure_icons_loaded(self):
        """Ensure file icons are loaded for use in exports"""
        if FileTypeIcons._icons is None:
            FileTypeIcons.load_icons()
    
    def _format_size(self, size: int) -> str:
        """Format file size for human readability"""
        if size is None:
            return '-'
        
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"
    
    def _get_formatted_data(self) -> List[Dict[str, Any]]:
        """Get formatted data for export with proper URL encoding"""
        formatted_data = []
        for result in self.results:
            try:
                mtime = datetime.fromtimestamp(result.path.stat().st_mtime)
                timestamp_raw = int(mtime.timestamp())  # Added for sorting
            except (OSError, AttributeError):
                mtime = datetime.now()
                timestamp_raw = int(mtime.timestamp())
                
            # Convert path to absolute and format for URL
            abs_path = str(result.path.absolute())
            # Handle Windows paths specifically
            if os.name == 'nt':
                url_path = abs_path.replace('\\', '/')
            else:
                url_path = abs_path
                
            # URL encode the path while preserving slashes
            url_path = quote(url_path, safe='/:\\')
                
            formatted_data.append({
                'icon': FileTypeIcons.get_icon(result.path),
                'type': 'Directory' if result.is_dir else 'File',
                'path': url_path,  # URL-encoded path
                'display_path': abs_path,  # Original path for display
                'relative_path': result.match_context,
                'size': self._format_size(result.size),
                'raw_size': result.size or 0,
                'timestamp': mtime.strftime('%Y-%m-%d %H:%M:%S'),
                'timestamp_raw': timestamp_raw  # Added for sorting
            })
        return formatted_data

    def export_csv(self, output_path: Path) -> None:
        """Export search results to CSV format"""
        data = self._get_formatted_data()
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'type', 'path', 'relative_path', 'size', 'timestamp'
            ])
            writer.writeheader()
            for row in data:
                writer.writerow({
                    'type': row['type'],
                    'path': row['path'],
                    'relative_path': row['relative_path'],
                    'size': row['size'],
                    'timestamp': row['timestamp']
                })

    def export_html(self, output_path: Path) -> None:
        """
        Export search results to HTML with theme support
        
        Args:
            output_path: Path where to save the HTML file
        """
        try:
            # Get unified template from resources
            template_content = ResourcesManager.get_template('search_template.html')
            
            # Calculate total size
            total_bytes = sum(item['raw_size'] for item in self._get_formatted_data())
            total_size = self._format_size(total_bytes)

            # Create Jinja2 environment with autoescape
            env = Environment(autoescape=True)
            template = env.from_string(template_content)

            # Render template with data
            rendered_html = template.render(
                results=self._get_formatted_data(),
                current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                total_size=total_size
            )

            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(rendered_html)
        except Exception as e:
            raise Exception(f"Failed to export HTML: {str(e)}")