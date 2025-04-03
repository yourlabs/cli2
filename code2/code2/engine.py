import os

from .project import Project


class Engine:
    def __init__(self):
        self.project = Project(os.getcwd())
