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

from code2.model import Model


class Prompt:
    """
    Build prompts from text files and context variables.
    """

    def __init__(self, *prompts, project=None, **context):
        if not project:
            from .project import Project
            project = Project()
        self.project = project
        self.parts = []
        for prompt in prompts:
            self.read(prompt)
        self.context = context

    @cli2.cmd(color='green', condition=lambda obj: not obj.parts)
    def paths(self, _cli2=None):
        """ Prompt directories paths ordered by priority """
        paths = [
            # project prompt overrides
            Path(self.project.path) / f'.code2/prompts',
            # user prompt overrides
            Path(os.getenv('HOME')) / f'.code2/prompts',
            # code2 defaults
            Path(__file__).parent / f'prompts',
        ]
        if _cli2:
            return [str(p) for p in paths]
        return paths

    def names(self):
        """ List prompt names """
        names = set()
        for path in self.paths():
            if not path.exists():
                continue
            for file in path.iterdir():
                names.add(file.name[:-4])
        return list(names)

    def find(self, name):
        """
        Find the prompt path by name

        :param name: Name of the prompt, as returned by names
        """
        for path in self.paths():
            path = path / f'{name}.txt'
            if path.exists():
                return path
        raise Exception(f'prompt {name} not found, tried {paths}')

    def read(self, name):
        """
        Read a prompt text file by name.

        :param name: Name of the prompt, as returned by names
        """
        path = self.find(name)
        with path.open('r') as f:
            content = f.read()
            cli2.log.debug(
                'prompt loaded',
                path=str(path),
                content=content,
            )
            self.parts.append(content)
            return content

    def render(self, **context):
        # extra context passed directly have priority
        final = self.context.copy()
        final.update(context)

        # add the project to the context
        final.setdefault('project', self.project)

        # build a jinja2 environment ...
        env = jinja2.Environment()

        # ... in which you can hook your plugins
        plugins = importlib.metadata.entry_points(
            group='code2_jinja2',
        )
        for plugin in plugins:
            env.globals[plugin.name] = plugin.load()

        # Render the template with the data
        template = env.from_string('\n'.join(self.parts))
        return template.render(**final)

    def messages(self, **context):
        final = self.context.copy()
        final.update(context)
        messages = []
        messages.append(
            dict(
                role='user',
                content=self.render(**final),
            ),
        )
        return messages


class ListParseMixin:
    def parse(self, response):
        results = []
        for line in response.splitlines():
            match = re.match('^- (.*)$', line)
            if match:
                results.append(match.group(1).strip())
        return results


FILES_PROMPT_SYSTEM = '''
You are an queried by an automated AI coding assistant program, your reply must
be structured for parsing.

Only reply with a list of complete file paths like this:
- path/to/file1
- path/to/file2
'''.strip()


class FilesPrompt(ListParseMixin, Prompt):
    def messages(self, request):
        return [
            dict(
                role='system',
                content=FILES_PROMPT_SYSTEM,
            ),
            dict(
                role='user',
                content=request,
            ),
        ]


DIRECTORIES_PROMPT_SYSTEM = '''
You are an queried by an automated AI coding assistant program, your reply must
be structured for parsing.

Only reply with a list of directories like this:
- path/to/directory1
- path/to/directory2
'''.strip()


class DirectoriesPrompt(ListParseMixin, Prompt):
    def messages(self, request):
        return [
            dict(
                role='system',
                content=DIRECTORIES_PROMPT_SYSTEM,
            ),
            dict(
                role='user',
                content=request,
            ),
        ]
