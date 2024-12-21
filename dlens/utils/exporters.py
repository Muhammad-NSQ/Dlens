import csv
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from jinja2 import Environment
import os
from urllib.parse import quote
import logging

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
        """Get formatted data with error handling"""
        formatted_data = []
        for result in self.results:
            try:
                mtime = datetime.fromtimestamp(result.path.stat().st_mtime)
            except (OSError, AttributeError):
                mtime = datetime.now()
                
            abs_path = str(result.path.absolute())
            if os.name == 'nt':
                url_path = abs_path.replace('\\', '/')
            else:
                url_path = abs_path
                
            url_path = quote(url_path, safe='/:\\')
            
            formatted_data.append({
                'icon': FileTypeIcons.get_icon(result.path),
                'type': 'Directory' if result.is_dir else 'File',
                'path': url_path,
                'display_path': abs_path,
                'relative_path': result.match_context,
                'size': self._format_size(result.size),
                'raw_size': result.size or 0,
                'timestamp': mtime.strftime('%Y-%m-%d %H:%M:%S'),
                'error': result.error if hasattr(result, 'error') else None
            })
        return formatted_data

    def export_csv(self, output_path: Path) -> None:
        """Export search results to CSV format with enhanced error handling"""
        try:
            data = self._get_formatted_data()
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    'type',
                    'path',
                    'relative_path',
                    'size',
                    'timestamp',
                    'error',  # Add error field
                    'is_directory',  # Additional useful info
                    'file_extension'  # Additional useful info
                ]
                
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in data:
                    try:
                        writer.writerow({
                            'type': row['type'],
                            'path': row['display_path'],  # Use display_path for better readability
                            'relative_path': row['relative_path'],
                            'size': row['size'],
                            'timestamp': row['timestamp'],
                            'error': row.get('error', ''),  # Add error info if present
                            'is_directory': 'Yes' if row['type'] == 'Directory' else 'No',
                            'file_extension': Path(row['display_path']).suffix if row['type'] == 'File' else ''
                        })
                    except Exception as e:
                        logging.warning(f"Error writing row for {row.get('path', 'unknown path')}: {str(e)}")
                        # Continue with next row instead of failing entire export
                        continue
                        
        except PermissionError:
            raise Exception(f"Permission denied when writing to {output_path}")
        except Exception as e:
            raise Exception(f"Failed to export CSV: {str(e)}")

    def export_html(self, output_path: Path) -> None:
        """
        Export search results to HTML with theme support and enhanced statistics
        
        Args:
            output_path: Path where to save the HTML file
        """
        try:
            # Get unified template from resources
            template_content = ResourcesManager.get_template('search_template.html')
            
            # Get formatted data for all results
            formatted_data = self._get_formatted_data()
            
            # Calculate statistics
            total_bytes = sum(item['raw_size'] for item in formatted_data)
            error_count = sum(1 for item in formatted_data if item.get('error'))
            file_count = sum(1 for item in formatted_data if not item.get('is_directory'))
            dir_count = sum(1 for item in formatted_data if item.get('is_directory'))

            # Create statistics dictionary
            stats = {
                'total_items': len(formatted_data),
                'total_size': self._format_size(total_bytes),
                'error_count': error_count,
                'file_count': file_count,
                'directory_count': dir_count,
                'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            # Create Jinja2 environment with autoescape
            env = Environment(autoescape=True)
            template = env.from_string(template_content)

            # Render template with enhanced data
            rendered_html = template.render(
                results=formatted_data,
                stats=stats,
                current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )

            # Ensure parent directories exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to file with proper encoding
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(rendered_html)
                
        except Exception as e:
            raise Exception(f"Failed to export HTML: {str(e)}")