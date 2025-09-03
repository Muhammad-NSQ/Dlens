from pathlib import Path
import re
import fnmatch
import logging
import os
from typing import Iterator, Pattern, List, Optional
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

@dataclass
class SearchResult:
    path: Path
    match_context: str
    is_dir: bool
    size: Optional[int] = None

class SearchHandler:
    def __init__(
        self,
        root_path: Path,
        pattern: str,
        use_regex: bool = False,
        case_sensitive: bool = True,
        max_results: Optional[int] = None,
        max_depth: Optional[int] = None,
        follow_symlinks: bool = False,
        show_hidden: bool = False,
        max_workers: int = None
    ):
        self.root_path = Path(root_path)
        self.pattern = self._validate_pattern(pattern)
        self.use_regex = use_regex
        self.case_sensitive = case_sensitive
        self.max_results = max_results
        self.max_depth = max_depth
        self.follow_symlinks = follow_symlinks
        self.show_hidden = show_hidden
        
        # Set reasonable max_workers based on system
        if max_workers is None:
            max_workers = min(4, (os.cpu_count() or 1) + 1)
        self.max_workers = max_workers
        
        self.executor = None  # Initialize lazily
        self._compile_pattern()
        
    def _validate_pattern(self, pattern: str) -> str:
        """Validate and sanitize search pattern"""
        if not pattern or not pattern.strip():
            raise ValueError("Search pattern cannot be empty")
        
        pattern = pattern.strip()
        if len(pattern) > 1000:  # Reasonable limit
            raise ValueError("Search pattern too long (max 1000 characters)")
            
        return pattern
        
    def _compile_pattern(self) -> None:
        """Compile pattern with proper error handling"""
        try:
            if self.use_regex:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                self._matcher = re.compile(self.pattern, flags)
            else:
                # Use fnmatch for shell-style wildcards
                translated_pattern = fnmatch.translate(self.pattern)
                flags = 0 if self.case_sensitive else re.IGNORECASE
                self._matcher = re.compile(translated_pattern, flags)
        except re.error as e:
            logging.error(f"Pattern compilation failed: {e}")
            raise ValueError(f"Invalid pattern: {e}")
                
    def _should_process(self, path: Path, current_depth: int) -> bool:
        """Check if path should be processed with error handling"""
        try:
            # Check hidden files
            if not self.show_hidden and path.name.startswith('.'):
                return False
            
            # Check depth limit
            if self.max_depth is not None and current_depth > self.max_depth:
                return False
            
            # Check symlinks
            if not self.follow_symlinks and path.is_symlink():
                return False
                
            # Check if path exists and is accessible
            return path.exists()
            
        except (PermissionError, OSError) as e:
            logging.debug(f"Cannot access path {path}: {e}")
            return False
        
    def _matches_pattern(self, path: Path) -> bool:
        """Check if path matches pattern with error handling"""
        try:
            return bool(self._matcher.search(path.name))
        except Exception as e:
            logging.warning(f"Pattern matching error for {path}: {e}")
            return False
        
    def _create_result(self, path: Path) -> SearchResult:
        """Create search result with error handling"""
        try:
            # Get file size safely
            size = None
            if path.is_file():
                try:
                    size = path.stat().st_size
                except (PermissionError, OSError):
                    size = None
            
            # Create relative path for display
            try:
                relative_path = str(path.relative_to(self.root_path))
            except ValueError:
                # Fallback if path is not relative to root
                relative_path = str(path)
            
            return SearchResult(
                path=path,
                match_context=relative_path,
                is_dir=path.is_dir(),
                size=size
            )
        except Exception as e:
            logging.error(f"Error creating result for {path}: {e}")
            # Return a basic result even if there's an error
            return SearchResult(
                path=path,
                match_context=str(path),
                is_dir=False,
                size=None
            )
        
    def search(self) -> Iterator[SearchResult]:
        """Non-parallel search with proper resource management"""
        result_count = 0
        
        def _search_dir(path: Path, depth: int = 0) -> Iterator[SearchResult]:
            nonlocal result_count
            
            # Check if we should process this path
            if not self._should_process(path, depth):
                return
                
            # Check result limit
            if self.max_results and result_count >= self.max_results:
                return
                
            try:
                # Use iterator instead of loading all entries into memory
                entries = path.iterdir()
                
                for entry in entries:
                    # Check limits again
                    if self.max_results and result_count >= self.max_results:
                        break
                        
                    if not self._should_process(entry, depth + 1):
                        continue
                        
                    # Check if entry matches pattern
                    if self._matches_pattern(entry):
                        result = self._create_result(entry)
                        yield result
                        result_count += 1
                        
                    # Recurse into directories
                    if entry.is_dir() and self._should_process(entry, depth + 1):
                        try:
                            yield from _search_dir(entry, depth + 1)
                        except RecursionError:
                            logging.warning(f"Maximum recursion depth exceeded at {entry}")
                            break
                            
            except PermissionError as e:
                logging.warning(f"Permission denied accessing {path}: {e}")
            except FileNotFoundError as e:
                logging.warning(f"Path not found {path}: {e}")
            except OSError as e:
                logging.warning(f"OS error accessing {path}: {e}")
            except Exception as e:
                logging.error(f"Unexpected error in directory {path}: {e}")
                    
        try:
            yield from _search_dir(self.root_path)
        finally:
            # Cleanup any resources
            if self.executor:
                self.executor.shutdown(wait=True)
            
    def search_parallel(self, chunk_size: int = 100) -> Iterator[SearchResult]:
        """Parallel search with better memory management and cleanup"""
        if not self.executor:
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            
        result_count = 0
        
        def _get_directory_chunks(path: Path, max_depth: Optional[int] = None) -> Iterator[List[Path]]:
            """Get directory entries in chunks to manage memory"""
            chunk = []
            
            try:
                for entry in path.rglob('*'):
                    # Check depth limit
                    if max_depth is not None:
                        try:
                            depth = len(entry.relative_to(path).parents)
                            if depth > max_depth:
                                continue
                        except ValueError:
                            continue
                    
                    chunk.append(entry)
                    
                    if len(chunk) >= chunk_size:
                        yield chunk
                        chunk = []
                        
                if chunk:
                    yield chunk
                    
            except (PermissionError, OSError) as e:
                logging.warning(f"Error walking directory {path}: {e}")
                if chunk:
                    yield chunk
                    
        def _process_chunk(paths: List[Path]) -> List[SearchResult]:
            """Process a chunk of paths"""
            results = []
            
            for path in paths:
                try:
                    if not self._should_process(path, len(path.parents)):
                        continue
                        
                    if self._matches_pattern(path):
                        result = self._create_result(path)
                        results.append(result)
                        
                except Exception as e:
                    logging.debug(f"Error processing path {path}: {e}")
                    continue
                    
            return results
            
        try:
            futures = []
            
            # Process chunks in parallel
            for chunk in _get_directory_chunks(self.root_path, self.max_depth):
                if self.max_results and result_count >= self.max_results:
                    break
                    
                future = self.executor.submit(_process_chunk, chunk)
                futures.append(future)
                
            # Collect results from futures
            for future in futures:
                try:
                    chunk_results = future.result(timeout=30)  # 30 second timeout
                    for result in chunk_results:
                        if self.max_results and result_count >= self.max_results:
                            return
                        yield result
                        result_count += 1
                except Exception as e:
                    logging.error(f"Error processing chunk: {e}")
                    continue
                    
        finally:
            # Ensure cleanup
            if self.executor:
                try:
                    self.executor.shutdown(wait=True)
                except Exception as e:
                    logging.error(f"Error shutting down executor: {e}")
                finally:
                    self.executor = None
                    
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        if self.executor:
            try:
                self.executor.shutdown(wait=True)
            except Exception as e:
                logging.error(f"Error in cleanup: {e}")
            finally:
                self.executor = None