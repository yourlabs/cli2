from pathlib import Path
import os
import sqlite3

from .scan import scan_repo


class Project:
    def __init__(self, path):
        self.path = Path(path)

    def scan(self):
        scan_repo(self.path)

    def files(self):
        DB_FILE = 'repo_symbols.db'
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('select path from files')
        return [row[0][len(os.getcwd()) + 1:] for row in cursor.fetchall()]
