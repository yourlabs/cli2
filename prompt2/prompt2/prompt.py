"""
Prompt management.
"""
import cli2
import functools
import importlib.metadata
from pathlib import Path
import os
import re

import jinja2

from .exception import NotFoundError
from .model import Model


class PromptType(type):
    @property
    def user_path(cls):
        if 'PROMPT2_USER_PATH' in os.environ:
            return Path(os.getenv('PROMPT2_USER_PATH'))
        else:
            return Path(os.getenv('HOME')) / '.prompt2/prompts'

    @property
    def local_path(cls):
        if 'PROMPT2_LOCAL_PATH' in os.environ:
            return Path(os.getenv('PROMPT2_LOCAL_PATH'))
        else:
            return Path(os.getcwd()) / '.prompt2/prompts'


class Prompt(metaclass=PromptType):
    """
    Build prompts from text files and context variables.
    """
    entry_point = 'prompt2_paths'

    class NotFoundError(NotFoundError):
        pass

    def __init__(self, path=None, content=None, **context):
        self.path = path
        self.content = content
        self.context = context

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        try:
            path = Path(value)
        except TypeError:
            pass
        else:
            if not path.exists():
                path = self.find(value)
            self._path = path

    @property
    def name(self):
        return self.path.name[:4]

    @property
    def content(self):
        if not self._content:
            with self.path.open('r') as f:
                self._content = f.read()
            cli2.log.debug(
                'prompt loaded',
                path=str(self.path),
                content=self._content,
            )
        return self._content

    @content.setter
    def content(self, value):
        self._content = value

    @classmethod
    def default_paths(cls, _cli2=None):
        paths = [cls.local_path]
        if cls.user_path != cls.local_path:
            # don't append when in home
            paths.append(cls.user_path)
        if _cli2:
            return [str(p) for p in paths]
        return paths

    @classmethod
    def paths(cls):
        plugins = importlib.metadata.entry_points(
            group=cls.entry_point,
        )
        paths = cls.default_paths()
        for plugin in plugins:
            paths += plugin.load()()
        return paths

    @classmethod
    def find(cls, name, paths=None):
        paths = paths or cls.paths()
        for path in paths:
            path = path / f'{name}.txt'
            if path.exists():
                return path
        raise cls.NotFoundError(name, paths)

    @classmethod
    def names(cls, paths=None):
        """ List prompt names """
        paths = paths or cls.default_paths()
        names = set()
        for path in self.paths():
            if not path.exists():
                continue
            for file in path.iterdir():
                names.add(file.name[:-4])
        return list(names)

    def render(self):
        # collect all paths from path plugins ...
        plugins = importlib.metadata.entry_points(
            group='prompt2_paths',
        )
        paths = [
            plugin.load()() for plugin in plugins
        ]

        # ... to build a jinja2 environment ...
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(
                [str(p) for p in paths],
            ),
            undefined=jinja2.StrictUndefined,
            autoescape=False,
        )

        # ... in which you can hook your plugins
        plugins = importlib.metadata.entry_points(
            group='prompt2_globals',
        )
        for plugin in plugins:
            env.globals[plugin.name] = plugin.load()

        # Render the template with the data
        template = env.from_string(self.content)
        return template.render(**self.context)

    def messages(self):
        messages = [
            dict(
                role='user',
                content=self.render(),
            ),
        ]
        return messages
