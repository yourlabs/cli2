
import aiofiles
from code2 import db
from sqlalchemy.orm import joinedload
from sqlalchemy import select


class SymbolsManager:
    def __init__(self, project):
        self.project = project

    async def src(self, *names):
        codes = []

        async with await self.project.db.session() as session:
            # Query symbols with related file data
            stmt = (
                select(db.Symbol)
                .where(db.Symbol.name.in_(names))
                .options(joinedload(db.Symbol.file))
            )
            result = await session.execute(stmt)
            symbols = result.unique().scalars().all()

            for symbol in symbols:
                code = None
                if not symbol.file or not symbol.file.path:
                    continue

                # Construct absolute file path
                file_path = (self.project.path / symbol.file.path).resolve()
                if file_path.is_file():
                    async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
                        # Read all lines
                        lines = await f.readlines()
                        # Convert to 0-based indexing (assuming database uses 1-based)
                        start = max(0, symbol.line_start - 1)
                        end = symbol.line_end if symbol.line_end is not None else symbol.line_start
                        end = min(len(lines), end)  # Ensure we don't go past file end

                        if start < len(lines):
                            # Extract the code lines
                            code_lines = lines[start:end]
                            code = ''.join(code_lines).rstrip()

                codes.append(code)

        return [c for c in codes if c]

    async def files(self, *names):
        """
        Retrieve the list of file paths related to a given list of symbol
        names.

        :param names: Variable number of symbol names to look up

        :return: List of file paths (strings) related to the symbols
        """
        file_paths = []

        async with await self.session() as session:
            # Query symbols with related file data
            stmt = (
                select(db.Symbol)
                .where(db.Symbol.name.in_(names))
                .options(joinedload(db.Symbol.file))
            )
            result = await session.execute(stmt)
            symbols = result.unique().scalars().all()

            for symbol in symbols:
                if symbol.file and symbol.file.path:
                    # Construct absolute file path
                    file_path = (self.path / symbol.file.path).resolve()
                    if file_path.is_file():
                        file_paths.append(str(file_path))

        return file_paths

    async def list( self, include=None, exclude=None, paths=None,):
        """
        List all symbols from the database with optional filters on symbol names and file paths.

        Args:
            include: Optional list of symbol name patterns to include (SQL LIKE syntax)
            exclude: Optional list of symbol name patterns to exclude (SQL LIKE syntax)
            paths: Optional list of file path patterns to filter on (SQL LIKE syntax)

        Returns:
            List of dictionaries containing symbol information
        """
        # Get session factory
        session_factory = await connect()

        async with session_factory() as session:
            # Base query with join to File table
            query = select(Symbol).join(File, Symbol.file_id == File.id)

            # Apply include filters on symbol names if provided
            if include:
                like_conditions = [Symbol.name.like(pattern) for pattern in include]
                query = query.where(or_(*like_conditions))

            # Apply exclude filters on symbol names if provided
            if exclude:
                unlike_conditions = [~Symbol.name.like(pattern) for pattern in exclude]
                query = query.where(and_(*unlike_conditions))

            # Apply path filters if provided
            if paths:
                path_conditions = [File.path.like(pattern) for pattern in paths]
                query = query.where(or_(*path_conditions))

            # Execute query
            result = await session.execute(query)
            symbols = result.scalars().all()

            # Format results as dictionaries
            symbol_list = [
                {
                    "id": symbol.id,
                    "file_id": symbol.file_id,
                    "type": symbol.type,
                    "name": symbol.name,
                    "line_start": symbol.line_start,
                    "line_end": symbol.line_end,
                    "score": symbol.score,
                    "file_path": symbol.file.path  # Added file path to output
                }
                for symbol in symbols
            ]

            return symbol_list
