from tree_sitter import Parser
from tree_sitter_language_pack import get_language, get_parser, SupportedLanguage
import os
import asyncio
from typing import List, Dict
from sqlalchemy import select, delete
import cli2  # Assuming this is where the Queue class comes from
from code2 import db

import_queries = {
    'python': """
    [
        (import_statement) @import
        (import_from_statement) @import_from
    ]
    """,
    'java': """
    (import_declaration) @import
    """,
    'cpp': """
    (include_directive) @include
    """
}

language_id_map = {'python': 1, 'java': 2, 'cpp': 3}
symbol_type_map = {'python': 'import', 'java': 'import', 'cpp': 'include'}

class ImportAnalyzer:
    def __init__(self, file_paths: List[str], language_name: str):
        self.file_paths = file_paths
        self.language_name = language_name
        self.language = get_language(language_name)
        self.parser= get_parser(self.language_name)
        self.query_str = import_queries.get(language_name)
        if not self.query_str:
            raise ValueError(f"No import query for {language_name}")
        self.query = self.language.query(self.query_str)
        self.file_id_map: Dict[str, int] = {}  # Cache file IDs
        self.queue = cli2.Queue()  # Using default num_workers

    async def _read_file(self, file_path: str) -> str:
        """Asynchronously read file content."""
        loop = asyncio.get_event_loop()
        with open(file_path, "r", encoding="utf-8") as f:
            return await loop.run_in_executor(None, f.read)

    async def _ensure_file_in_db(self, session, file_path: str) -> int:
        """Ensure file exists in DB and return its ID."""
        if file_path in self.file_id_map:
            return self.file_id_map[file_path]

        result = await session.execute(select(db.File).where(db.File.path == file_path))
        file = result.scalar_one_or_none()

        if not file:
            file = db.File(
                path=file_path,
                mtime=os.path.getmtime(file_path),
                language_id=language_id_map.get(self.language_name, 1),
                token_count=0
            )
            session.add(file)
            await session.flush()
            self.file_id_map[file_path] = file.id
        else:
            self.file_id_map[file_path] = file.id
        return self.file_id_map[file_path]

    async def _find_or_create_symbol(self, session, file_id: int,
                                   symbol_name: str, line_number: int) -> int:
        """Find or create a symbol and return its ID."""
        result = await session.execute(
            select(db.Symbol).where(
                db.Symbol.file_id == file_id,
                db.Symbol.name == symbol_name,
                db.Symbol.line_number == line_number
            )
        )
        symbol = result.scalar_one_or_none()

        if not symbol:
            symbol_type = symbol_type_map.get(self.language_name, 'dependency')
            symbol = db.Symbol(
                file_id=file_id,
                type=symbol_type,
                name=symbol_name,
                line_number=line_number,
                score=5
            )
            session.add(symbol)
            await session.flush()
            return symbol.id
        return symbol.id

    async def _add_import(self, session, symbol_id: int, file_id: int):
        """Add import entry if it doesn't exist."""
        result = await session.execute(
            select(db.Import).where(
                db.Import.symbol_id == symbol_id,
                db.Import.file_id == file_id
            )
        )
        if not result.scalar_one_or_none():
            import_entry = db.Import(symbol_id=symbol_id, file_id=file_id)
            session.add(import_entry)

    async def _analyze_file(self, file_path: str):
        """Analyze a single file and store its imports."""
        session_factory = await db.connect()
        async with session_factory() as session:
            try:
                code = await self._read_file(file_path)
                tree = self.parser.parse(bytes(code, "utf-8"))
                imports = self.query.captures(tree.root_node)
                file_id = await self._ensure_file_in_db(session, file_path)

                for node in imports['import']:
                    line_number = node.start_point[0] + 1
                    if node.type == "import_statement":
                        symbol_name = node.children[0].text.decode("utf-8")
                    elif node.type == "import_from_statement":
                        symbol_name = f"{node.children[0].text.decode('utf-8')}.{node.children[1].text.decode('utf-8')}"
                    else:
                        continue

                    symbol_id = await self._find_or_create_symbol(
                        session, file_id, symbol_name, line_number)
                    await self._add_import(session, symbol_id, file_id)

                # Commit all changes after all tasks are complete
                await session.commit()
                return True  # Return success indicator
            except Exception as e:
                cli2.log.exception(f"Error processing {file_path}: {str(e)}")
                await session.rollback()
                return False  # Return failure indicator

    async def analyze_and_store_imports(self):
        """Analyze all files using the queue and store imports."""
        # Create tasks for each file
        tasks = [
            self._analyze_file(file_path)
            for file_path in self.file_paths
        ]

        # Run tasks through the queue
        await self.queue.run(*tasks)

        # Optionally check results
        if self.queue.results:
            successful = sum(1 for r in self.queue.results if r)
            print(f"Processed {successful}/{len(self.file_paths)} files successfully")
