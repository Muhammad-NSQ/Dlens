from pathlib import Path
import re
import fnmatch
from typing import Iterator, Pattern, List, Optional
from concurrent.futures import ThreadPoolExecutor
import logging
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
        max_workers: int = 4
    ):
        self.root_path = Path(root_path)
        self.pattern = pattern
        self.use_regex = use_regex
        self.case_sensitive = case_sensitive
        self.max_results = max_results
        self.max_depth = max_depth
        self.follow_symlinks = follow_symlinks
        self.show_hidden = show_hidden
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._compile_pattern()
        
    def _compile_pattern(self) -> None:
        if self.use_regex:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            try:
                self._matcher = re.compile(self.pattern, flags)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        else:
            self._matcher = fnmatch.translate(self.pattern)
            flags = 0 if self.case_sensitive else re.IGNORECASE
            self._matcher = re.compile(self._matcher, flags)
                
    def _should_process(self, path: Path, current_depth: int) -> bool:
        if not self.show_hidden and path.name.startswith('.'):
            return False
        if self.max_depth is not None and current_depth > self.max_depth:
            return False
        if not self.follow_symlinks and path.is_symlink():
            return False
        return True
        
    def _matches_pattern(self, path: Path) -> bool:
        return bool(self._matcher.search(path.name))
        
    def _create_result(self, path: Path) -> SearchResult:
        try:
            size = path.stat().st_size if path.is_file() else None
        except (PermissionError, OSError):
            size = None
            
        return SearchResult(
            path=path,
            match_context=str(path.relative_to(self.root_path)),
            is_dir=path.is_dir(),
            size=size
        )
        
    def search(self) -> Iterator[SearchResult]:
        result_count = 0
        
        def _search_dir(path: Path, depth: int = 0) -> Iterator[SearchResult]:
            nonlocal result_count
            
            if not self._should_process(path, depth):
                return
                
            try:
                entries = list(path.iterdir())
            except (PermissionError, OSError) as e:
                logging.warning(f"Access denied to {path}: {e}")
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
                    
                if entry.is_dir():
                    yield from _search_dir(entry, depth + 1)
                    
        try:
            yield from _search_dir(self.root_path)
        finally:
            self.executor.shutdown(wait=False)
            
    def search_parallel(self, chunk_size: int = 1000) -> Iterator[SearchResult]:
        """Parallel search implementation for large directories"""
        def _chunk_walker(path: Path) -> List[Path]:
            chunk = []
            for entry in path.rglob('*'):
                if len(chunk) >= chunk_size:
                    yield chunk
                    chunk = []
                chunk.append(entry)
            if chunk:
                yield chunk
                
        def _process_chunk(paths: List[Path]) -> List[SearchResult]:
            results = []
            for path in paths:
                if self._should_process(path, len(path.parents)):
                    if self._matches_pattern(path):
                        results.append(self._create_result(path))
            return results
            
        try:
            futures = []
            for chunk in _chunk_walker(self.root_path):
                if self.max_results and sum(len(f.result()) if f.done() else 0 for f in futures) >= self.max_results:
                    break
                futures.append(self.executor.submit(_process_chunk, chunk))
                
            for future in futures:
                for result in future.result():
                    if self.max_results and sum(len(f.result()) if f.done() else 0 for f in futures) >= self.max_results:
                        return
                    yield result
        finally:
            self.executor.shutdown(wait=False)