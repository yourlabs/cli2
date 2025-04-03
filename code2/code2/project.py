import cli2
import functools

from pathlib import Path
import os
import sqlite3

from .context import Context
from .scan import scan_repo


class Project:
    def __init__(self, path):
        self.path = Path(path)
        self._contexts = dict()

    @property
    def contexts(self):
        """ Return a dict of contexts, create a default context if necessary """
        for path in self.contexts_path.iterdir():
            if path.name not in self._contexts:
                self._contexts[path.name] = Context(self, path)

        if 'default' not in self._contexts:
            self._contexts['default'] = Context(
                self,
                self.contexts_path / 'default',
            )
            self._contexts['default'].path.mkdir(exist_ok=True, parents=True)

        return self._contexts

    @functools.cached_property
    def contexts_path(self):
        """ Return the path to the project context directories """
        path = self.path / '.code2/contexts'
        path.mkdir(exist_ok=True, parents=True)
        return path

    @property
    def propmts(self):
        """ Return a dict of prompts, create a default context if necessary """
        for path in self.contexts_path.iterdir():
            if path.name not in self._contexts:
                self._contexts[path.name] = Context(self, path)

        if 'default' not in self._contexts:
            self._contexts['default'] = Context(
                self,
                self.contexts_path / 'default',
            )
            self._contexts['default'].path.mkdir(exist_ok=True, parents=True)

        return self._contexts

    @functools.cached_property
    def prompts_path(self):
        """ Return the path to the project context directories """
        path = self.path / '.code2/contexts'
        path.mkdir(exist_ok=True, parents=True)
        return path

    @cli2.cmd
    def scan(self):
        """ Run a projet scan """
        scan_repo(self.path)

    def files(self):
        """ Get files from project """
        DB_FILE = 'repo_symbols.db'
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('select path from files')
        return [row[0] for row in cursor.fetchall()]

    def symbols(self, where=None, *args):
        """ Get files from project """
        DB_FILE = 'repo_symbols.db'
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        where = f'and {where}' if where else ''
        sql = f'''
        select f.path, s.line_number, s.type, s.name
        from files f left join symbols s
        where f.id = s.file_id {where}
        order by f.path asc, s.line_number asc
        '''
        cursor.execute(sql, *args)
        return cursor.fetchall()

    def symbols_unique(self):
        DB_FILE = 'repo_symbols.db'
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('select distinct name from symbols')
        return [row[0] for row in cursor.fetchall()]

    def symbols_dump(self):
        result = ['List of file, line number, symbol type, symbol name:\n']
        for row in self.symbols():
            result.append(f'{row[0]}:{row[1]}:{row[2]}:{row[3]}')
        return '\n'.join(result)
