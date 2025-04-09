from sqlalchemy import select
from sqlalchemy.orm import joinedload
from typing import Dict, List, Optional
import json
import fnmatch
from . import db

class RepoMapGenerator:
    """Generates an optimized repository map with files and symbols for LLM consumption."""

    def __init__(
        self,
        session_factory,
        glob_include_files: Optional[List[str]] = None,
        glob_exclude_files: Optional[List[str]] = None,
        glob_include_symbols: Optional[List[str]] = None,
        glob_exclude_symbols: Optional[List[str]] = None
    ):
        """
        Initialize the RepoMapGenerator with optional glob patterns for filtering.

        Args:
            session_factory: SQLAlchemy async session factory
            glob_include_files: List of glob patterns to include files (e.g., ["*.py"])
            glob_exclude_files: List of glob patterns to exclude files (e.g., ["test/*"])
            glob_include_symbols: List of glob patterns to include symbols (e.g., ["test_*"])
            glob_exclude_symbols: List of glob patterns to exclude symbols (e.g., ["_*"])
        """
        self.session_factory = session_factory
        self.glob_include_files = glob_include_files or []
        self.glob_exclude_files = glob_exclude_files or []
        self.glob_include_symbols = glob_include_symbols or []
        self.glob_exclude_symbols = glob_exclude_symbols or []

    async def generate_map(self, max_size: int = 10000) -> Dict:
        """
        Generates a repository map with file structure and symbol names.

        Args:
            max_size: Maximum approximate size in characters for the output

        Returns:
            Dictionary containing the optimized repo map
        """
        async with self.session_factory() as session:
            # Get all files with their symbols eagerly loaded
            files_stmt = (
                select(db.File)
                .options(joinedload(db.File.symbols))
            )
            files_result = await session.execute(files_stmt)
            files = files_result.scalars().unique().all()

            # Build the map with filtering
            repo_map = {
                "files": await self._build_file_map(files),
            }

            # Optimize size if needed
            return await self._optimize_map(repo_map, max_size)

    def _decode(self, value):
        """Helper to decode bytes to string if necessary."""
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        return value

    def _match_glob(self, value: str, patterns: List[str], default: bool = True) -> bool:
        """Check if a value matches any glob pattern in the list."""
        if not patterns:
            return default
        return any(fnmatch.fnmatch(value, pattern) for pattern in patterns)

    async def _build_file_map(self, files) -> Dict:
        """Builds a map of files with their symbol names as a direct list, skipping empty files."""
        file_map = {}
        for file in files:
            path = self._decode(file.path)

            # Apply file filters
            include_file = self._match_glob(path, self.glob_include_files, default=True)
            exclude_file = self._match_glob(path, self.glob_exclude_files, default=False)
            if not include_file or exclude_file:
                continue

            # Apply symbol filters and build symbol list
            symbols = []
            if file.symbols:
                for sym in file.symbols:
                    name = self._decode(sym.name)
                    include_symbol = self._match_glob(name, self.glob_include_symbols, default=True)
                    exclude_symbol = self._match_glob(name, self.glob_exclude_symbols, default=False)
                    if include_symbol and not exclude_symbol:
                        symbols.append(name)

            # Only include file if it has symbols after filtering
            if symbols:
                file_map[path] = symbols

        return file_map

    async def _optimize_map(self, repo_map: Dict, max_size: int) -> Dict:
        """
        Optimizes the map to fit within size constraints.
        """
        # Convert to compact JSON string for size checking
        map_str = json.dumps(repo_map, separators=(',', ':'))

        if len(map_str) <= max_size:
            return repo_map

        # If too large, start pruning
        optimized = repo_map.copy()

        # Prune symbol lists
        for file_path in list(optimized["files"]):
            symbols = optimized["files"][file_path]
            if len(symbols) > 5:  # Adjust threshold as needed
                optimized["files"][file_path] = symbols[:5]
            # Remove file if no symbols remain after pruning
            if not optimized["files"][file_path]:
                del optimized["files"][file_path]

        return optimized

    async def get_map_string(self, max_size: int = 10000) -> str:
        """Returns the repo map as a compact formatted string."""
        repo_map = await self.generate_map(max_size)
        return json.dumps(repo_map, separators=(',', ':'))

# Example usage:
"""
async def main():
    session_factory = await db.connect()
    generator = RepoMapGenerator(
        session_factory,
        glob_include_files=['*.py', '*.js'],
        glob_exclude_files=['tests/*', '*_test.py'],
        glob_include_symbols=['get_*', 'set_*'],
        glob_exclude_symbols=['_*']
    )
    map_str = await generator.get_map_string()
    print(map_str)
    await db.close()
"""
