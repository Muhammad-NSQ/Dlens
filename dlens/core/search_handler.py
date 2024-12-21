from pathlib import Path
import re
import fnmatch
from typing import Iterator, Pattern, List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor
import logging
from dataclasses import dataclass
from contextlib import contextmanager
import os

@dataclass
class SearchResult:
    path: Path
    match_context: str
    is_dir: bool
    size: Optional[int] = None
    error: Optional[str] = None  # Added to track per-file errors

@dataclass
class SearchStats:
    """Statistics for search operation"""
    total_scanned: int = 0
    matches_found: int = 0
    errors_count: int = 0
    skipped_count: int = 0
    
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
        max_workers: int = 4,
        verbose: bool = False
    ):
        self.root_path = Path(root_path)
        self.pattern = pattern
        self.use_regex = use_regex
        self.case_sensitive = case_sensitive
        self.max_results = max_results
        self.max_depth = max_depth
        self.follow_symlinks = follow_symlinks
        self.show_hidden = show_hidden
        self.verbose = verbose
        self.stats = SearchStats()
        self.executor = None  # Will be initialized when needed
        self.max_workers = max_workers
        self._compile_pattern()
        
    @contextmanager
    def _get_executor(self):
        """Context manager for ThreadPoolExecutor"""
        try:
            self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
            yield self.executor
        finally:
            if self.executor:
                self.executor.shutdown(wait=True)
                self.executor = None

    def _compile_pattern(self) -> None:
        try:
            if self.use_regex:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                self._matcher = re.compile(self.pattern, flags)
            else:
                pattern = fnmatch.translate(self.pattern)
                flags = 0 if self.case_sensitive else re.IGNORECASE
                self._matcher = re.compile(pattern, flags)
        except re.error as e:
            raise ValueError(f"Invalid pattern: {e}")
        except Exception as e:
            raise ValueError(f"Pattern compilation error: {e}")

    def _should_process(self, path: Path, current_depth: int) -> bool:
        """Enhanced path processing check"""
        try:
            # Basic checks
            if not self.show_hidden and path.name.startswith('.'):
                self.stats.skipped_count += 1
                return False
                
            if self.max_depth is not None and current_depth > self.max_depth:
                self.stats.skipped_count += 1
                return False
                
            # Symlink handling
            if path.is_symlink():
                if not self.follow_symlinks:
                    self.stats.skipped_count += 1
                    return False
                # Check for symlink loops
                try:
                    path.resolve(strict=True)
                except RuntimeError:
                    if self.verbose:
                        logging.warning(f"Symlink loop detected at {path}")
                    self.stats.skipped_count += 1
                    return False
                    
            # Path length check (Windows)
            if os.name == 'nt' and len(str(path)) > 260:
                if self.verbose:
                    logging.warning(f"Path too long: {path}")
                self.stats.skipped_count += 1
                return False
                
            return True
            
        except Exception as e:
            if self.verbose:
                logging.warning(f"Error processing path {path}: {e}")
            self.stats.errors_count += 1
            return False

    def _matches_pattern(self, path: Path) -> bool:
        """Enhanced pattern matching with error handling"""
        try:
            name = path.name
            return bool(self._matcher.search(name))
        except Exception as e:
            if self.verbose:
                logging.warning(f"Pattern matching error for {path}: {e}")
            self.stats.errors_count += 1
            return False

    def _create_result(self, path: Path) -> SearchResult:
        """Enhanced result creation with error handling"""
        try:
            size = path.stat().st_size if path.is_file() else None
            return SearchResult(
                path=path,
                match_context=str(path.relative_to(self.root_path)),
                is_dir=path.is_dir(),
                size=size
            )
        except PermissionError:
            error_msg = "Permission denied"
            if self.verbose:
                logging.warning(f"Permission denied: {path}")
            self.stats.errors_count += 1
        except OSError as e:
            error_msg = f"OS Error: {e}"
            if self.verbose:
                logging.warning(f"OS Error for {path}: {e}")
            self.stats.errors_count += 1
        except Exception as e:
            error_msg = f"Error: {e}"
            if self.verbose:
                logging.warning(f"Error processing {path}: {e}")
            self.stats.errors_count += 1
            
        return SearchResult(
            path=path,
            match_context=str(path.relative_to(self.root_path)),
            is_dir=False,
            size=None,
            error=error_msg
        )

    def search(self) -> Iterator[SearchResult]:
        """Sequential search with enhanced error handling"""
        result_count = 0
        
        def _search_dir(path: Path, depth: int = 0) -> Iterator[SearchResult]:
            nonlocal result_count
            
            if not self._should_process(path, depth):
                return
                
            try:
                entries = list(path.iterdir())
                self.stats.total_scanned += len(entries)
            except (PermissionError, OSError) as e:
                if self.verbose:
                    logging.warning(f"Access denied to {path}: {e}")
                self.stats.errors_count += 1
                return
                
            for entry in entries:
                if self.max_results and result_count >= self.max_results:
                    return
                    
                if not self._should_process(entry, depth + 1):
                    continue
                    
                if self._matches_pattern(entry):
                    result = self._create_result(entry)
                    yield result
                    result_count += 1
                    self.stats.matches_found += 1
                    
                if entry.is_dir():
                    yield from _search_dir(entry, depth + 1)
                    
        try:
            yield from _search_dir(self.root_path)
        finally:
            if self.verbose:
                self._log_stats()

    def search_parallel(self, chunk_size: int = 1000) -> Iterator[SearchResult]:
        """Enhanced parallel search implementation"""
        result_count = 0
        
        def _chunk_walker(path: Path) -> List[Path]:
            chunk = []
            try:
                for entry in path.rglob('*'):
                    if len(chunk) >= chunk_size:
                        yield chunk
                        chunk = []
                    chunk.append(entry)
            except Exception as e:
                if self.verbose:
                    logging.warning(f"Error walking directory {path}: {e}")
            if chunk:
                yield chunk

        def _process_chunk(paths: List[Path]) -> List[SearchResult]:
            results = []
            for path in paths:
                try:
                    if self._should_process(path, len(path.parents)):
                        if self._matches_pattern(path):
                            results.append(self._create_result(path))
                except Exception as e:
                    if self.verbose:
                        logging.warning(f"Error processing path {path}: {e}")
            return results

        try:
            with self._get_executor() as executor:
                futures = []
                pending_results = []

                # Process chunks until we have enough results
                for chunk in _chunk_walker(self.root_path):
                    if self.max_results and result_count >= self.max_results:
                        break

                    future = executor.submit(_process_chunk, chunk)
                    futures.append(future)

                    # Check completed futures
                    completed = []
                    for future in futures:
                        if future.done():
                            completed.append(future)
                            try:
                                results = future.result()
                                for result in results:
                                    if self.max_results and result_count >= self.max_results:
                                        break
                                    result_count += 1
                                    self.stats.matches_found += 1
                                    yield result
                            except Exception as e:
                                if self.verbose:
                                    logging.warning(f"Error processing chunk: {e}")
                                self.stats.errors_count += 1

                    # Remove processed futures
                    for future in completed:
                        futures.remove(future)

                # Process remaining futures
                for future in futures:
                    try:
                        results = future.result()
                        for result in results:
                            if self.max_results and result_count >= self.max_results:
                                break
                            result_count += 1
                            self.stats.matches_found += 1
                            yield result
                    except Exception as e:
                        if self.verbose:
                            logging.warning(f"Error processing chunk: {e}")
                        self.stats.errors_count += 1

        finally:
            if self.verbose:
                self._log_stats()

    def _log_stats(self):
        """Log search statistics"""
        logging.info(f"Search completed:")
        logging.info(f"Total items scanned: {self.stats.total_scanned}")
        logging.info(f"Matches found: {self.stats.matches_found}")
        logging.info(f"Errors encountered: {self.stats.errors_count}")
        logging.info(f"Items skipped: {self.stats.skipped_count}")