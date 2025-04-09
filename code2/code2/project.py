from pathlib import Path
from sqlalchemy import select
from sqlalchemy.sql import or_, and_
from typing import List, Optional
import cli2
import functools
import os
import subprocess
import textwrap
from .context import Context
from . import db


class ProjectDB:
    _engine = None
    _session = None
    _session_factory = None

    @classmethod
    def engine(cls):
        if not cls._engine:
            cls._engine = db.create_async_engine(cli2.cfg["CODE2_DB"], echo=False)
        return cls._engine

    @classmethod
    async def session_factory(cls):
        if not cls._session_factory:
            #engine = db.create_engine(cli2.cfg["CODE2_DB"], echo=False)
            #db.Base.metadata.create_all(engine, checkfirst=True)
            #db.Base.metadata.create_all(cls.engine, checkfirst=True)
            async with cls.engine().begin() as conn:
                await conn.run_sync(lambda connection: db.Base.metadata.create_all(connection, checkfirst=True))

            cls._session_factory = db.async_sessionmaker(
                cls.engine(),
                class_=db.AsyncSession,
                expire_on_commit=False,
            )
        return cls._session_factory

    @classmethod
    async def session(cls):
        if not cls._session:
            cls._session = await cls.session_make()
        return cls._session

    @classmethod
    async def session_make(cls):
        return (await cls.session_factory())()

    @classmethod
    async def session_open(cls):
        if not cls._session:
            cls._session = await cls.session_factory()
        return cls._session

    @classmethod
    async def session_close(cls):
        if cls._session is not None:
            await cls.engine().dispose()


class Project(ProjectDB):
    current = None

    def __init__(self, path=None):
        self.path = Path(path or os.getcwd())
        self._contexts = dict()
        self._files = []
        self._files_symbols = dict()
        self.current = self
        cli2.cfg.defaults.update(dict(
            CODE2_DB=f'sqlite+aiosqlite:///{self.path}/.code2/db.sqlite3',
        ))

    def get_all_directories(self, path=None):
        path = path or self.path
        if not path.is_dir():
            return []
        directories = []
        for item in path.iterdir():
            if item.is_dir():
                directories.append(item)
                directories.extend(self.get_all_directories(item))
        return directories

    async def inspect(self):
        """
        Initialize a project.

        Test commands
        - What key files or commands are we going to use to understand language
          and dependencies versions?
        - How to run all tests?
        - How to run a single test?
        - How to run a single test with coverage?
        - Any specific test runner?
        - Any specifics providers of any sort that we can change when running the tests?

        Code style and guidelines
        - What naming conventions are used?
        - What import conventions?
        - What indentation and character line limit?
        - What kind of documentation in code?
        """
        raise NotImplementedError()

    @property
    def contexts(self):
        """Return a dict of contexts, create a default context if necessary."""
        for path in self.contexts_path.iterdir():
            if path.name not in self._contexts:
                self._contexts[path.name] = Context(self, path)

        for name in ('default', 'project'):
            if name in self._contexts:
                continue
            self._contexts[name] = Context(self, self.contexts_path / name)
            self._contexts[name].path.mkdir(exist_ok=True, parents=True)

        return self._contexts

    @functools.cached_property
    def contexts_path(self):
        """Return the path to the project context directories."""
        path = self.path / '.code2/contexts'
        path.mkdir(exist_ok=True, parents=True)
        return path

    @functools.cached_property
    def data_path(self):
        """Return the path to the project data directories."""
        path = self.path / '.code2/data'
        path.mkdir(exist_ok=True, parents=True)
        return path

    def save(self, key, data):
        """Save data to a file in data_path."""
        self.data_path.mkdir(exist_ok=True, parents=True)
        with (self.data_path / key).open('w') as f:
            f.write(data)

    def load(self, key):
        """Load data from a file in data_path."""
        path = self.data_path / key
        if not path.exists():
            return None
        with path.open('r') as f:
            return f.read()

    @cli2.cmd(name='scan')
    async def scan_dir(self):
        """
        Index files and symbols in the current directory.
        """
        from . import scan_dir
        indexer = scan_dir.CodeIndexer(self)
        return await indexer.index_repo_async()

    @cli2.cmd(name='scanf')
    async def scan_files(self, *files):
        """
        Index imports made by given files.
        """
        from . import scan_files
        indexer = scan_files.ImportAnalyzer(self, files, 'python')
        return await indexer.analyze_and_store_imports()

    @cli2.cmd(name='map')
    async def repo_map(self):
        """
        Index files and symbols in the current directory.
        """
        from . import repo_map
        from . import db
        generator = repo_map.RepoMapGenerator(self)
        map_str = await generator.get_map_string()
        print(map_str)


    async def list_symbols(
        self,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        paths: Optional[List[str]] = None
    ) -> List[dict]:
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
