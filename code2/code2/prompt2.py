from pathlib import Path
from code2.project import Project
import os


def paths():
    return [Path(__file__).parent / 'prompts']


project = Project(os.getcwd())
