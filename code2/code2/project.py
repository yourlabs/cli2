import cli2
import functools
import textwrap
import subprocess
from pathlib import Path
import os

from .context import Context


class Project:
    def __init__(self, path=None):
        self.path = Path(path or os.getcwd())
        self._contexts = dict()
        self._files = []
        self._files_symbols = dict()

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

    @cli2.cmd(something=False)
    def scan(self):
        """Run a project scan."""
        from . import scan
        scan.repo(self.path)

    def files(self):
        """Get files from project."""
        if self._files:
            return self._files

        # Populate from filesystem
        for dirpath, dirnames, filenames in self.path.walk():
            for filename in filenames:
                path = (dirpath / filename).relative_to(self.path)
                self._files.append(path)

        # Filter with gitignore
        from .scan import filter_paths
        self._files = filter_paths(self._files)
        return self._files

    @property
    def files_symbols(self):
        """Get symbols per file as a dictionary."""
        if not self._files_symbols:
            with scan.db:
                query = (File
                         .select(File.path, Symbol.line_number, Symbol.type, Symbol.name)
                         .left_outer_join(Symbol, on=(File.id == Symbol.file))
                         .order_by(File.path.asc(), Symbol.line_number.asc()))
                for row in query.tuples():
                    path, line_number, sym_type, name = row
                    if path not in self._files_symbols:
                        self._files_symbols[path] = {}
                    self._files_symbols[path][name] = [sym_type, line_number]
        return self._files_symbols

    def symbols(self, where=None, *args):
        """Get symbols from project with optional where clause."""
        with scan.db:
            query = (File
                     .select(File.path, Symbol.line_number, Symbol.type, Symbol.name)
                     .left_outer_join(Symbol, on=(File.id == Symbol.file))
                     .order_by(File.path.asc(), Symbol.line_number.asc()))
            if where:
                # Assuming 'where' is a raw SQL snippet; use Peewee expressions instead if possible
                query = query.where(SQL(where, *args))
            return [(row[0], row[1], row[2], row[3]) for row in query.tuples()]

    def symbols_unique(self):
        """Get unique symbol names."""
        with scan.db:
            query = Symbol.select(Symbol.name).distinct()
            return [row.name for row in query]

    def symbols_dump(self):
        """Dump symbols as a formatted string."""
        result = ['List of file, line number, symbol type, symbol name:\n']
        for path, line_number, sym_type, name in self.symbols():
            result.append(f'{path}:{line_number}:{sym_type}:{name}')
        return '\n'.join(result)

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

    def query(self, sql):
        """Execute a raw SQL query (fallback for complex cases)."""
        with scan.db:
            cursor = db.execute_sql(sql)
            return cursor.fetchall()

    def extensions(self):
        """Return list of distinct file extensions for this project."""
        with db:
            query = (File
                     .select(fn.SUBSTR(File.path, fn.INSTR(File.path, '.') + 1).alias('ext'))
                     .where(fn.INSTR(File.path, '.') > 0)
                     .distinct())
            return [row.ext for row in query]
