from pathlib import Path
from sqlalchemy.sql import or_, and_
from typing import List, Optional
import cli2
import functools
import os
import subprocess
import textwrap
from code2.project.symbols import SymbolsManager
from code2.project.db import ProjectDB
from code2.context import Context
from . import db


class ProjectMetaclass(type):
    @property
    def current(self):
        current = getattr(self, '_current', None)
        if not current:
            self._current = Project(os.getcwd())
        return self._current


class Project(metaclass=ProjectMetaclass):
    current = None

    def __init__(self, path=None):
        self.path = Path(path or os.getcwd())
        self.db = ProjectDB(self)

        self._contexts = dict()
        self.symbols = SymbolsManager(self)

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
        from code2.project import scan_dir
        indexer = scan_dir.CodeIndexer(self)
        return await indexer.index_repo_async()

    @cli2.cmd(name='scanf')
    async def scan_files(self, *files):
        """
        Index imports made by given files.
        """
        from code2.project import scan_files
        indexer = scan_files.ImportAnalyzer(self, files, 'python')
        return await indexer.analyze_and_store_imports()

    @cli2.cmd(name='map')
    async def repo_map(self):
        """
        Index files and symbols in the current directory.
        """
        from code2.project import repo_map
        generator = repo_map.RepoMapGenerator(self)
        map_str = await generator.get_map_string()
        print(map_str)



project = Project(os.getcwd())
