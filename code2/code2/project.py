from pathlib import Path

from .scan import scan_repo


class Project:
    def __init__(self, path):
        self.path = Path(path)

    def scan(self):
        scan_repo(self.path)
