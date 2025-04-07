"""
Base Workflowant plugin which you can inherit from.

Plugins register themselves over the ``code2_workflow`` entrypoint, and are
exposed on the command line for every context.

To create your own plugin, create a Python package with an entrypoint like:

.. code-block:: python

    'code2_workflow': [
        'plugin_name = your.module:ClassName',
    ]

Install the package and ``plugin_name`` will appear in the code2 command line.
"""

import asyncio
import cli2
import functools
import importlib.metadata
import os
import re
import shlex
import textwrap


class WorkflowPlugin:
    def __init__(self, project, context):
        self.project = project
        self.context = context
        self.llm_plugins = dict()

    @classmethod
    async def run_plugin(cls, project, context, *message, _cli2=None):
        # this is just a CLI wrapper
        if not message:
            return _cli2.help()
        obj = cls(project, context)
        return await obj.run(' '.join(message))

    async def run_command(self, *command):
        # Start the subprocess with pipes for stdout and stderr
        env = os.environ.copy()
        env['NO_TIMESTAMPER'] = '1'

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env
        )

        captured_output = []

        cli2.log.debug(
            'running',
            command=' '.join([shlex.quote(c) for c in command]),
        )
        async for line in process.stdout:
            print(line.decode('utf8'), end='')  # Display live
            captured_output.append(line)  # Capture it

        return_code = await process.wait()

        # Join captured lines into a single string
        full_output = b''.join(captured_output)
        full_output = full_output.decode('utf8')
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        full_output = ansi_escape.sub('', full_output)
        return full_output, return_code

    def context_files_dump(self):
        dump = []
        for file in self.context.files():
            dump.append(f'\n\nSource code of {file}:')
            with open(file, 'r') as f:
                dump.append(f.read())
        return '\n'.join(dump)

    def list_parse(self, response):
        results = []
        for line in response.splitlines():
            match = re.match('^- (.*)$', line)
            if match:
                results.append(match.group(1).strip())
        return results

    def prompt_data(self, name, request=None, models=None):
        if name in self.context.data:
            return self.context.data[name]

        prompt = self.prompt(name, models)
        result = prompt.process(request, **kwargs)
        self.context.data[name] = result
        self.context.save()

        return result

    def dependencies_refine_prompt(self, message):
        PROMPT = textwrap.dedent('''
        You are called from an automated AI assistant requiring a structured
        response.

        You are given a list of files in a project and find any file that could
        give clues about the used dependencies, such as requirements files,
        package definition files, and so on.

        {files}

        Reply ONLY with the list of file paths containing external dependencies in
        the format:
        - full/path/to/file1
        - full/path/to/file2
        ''').format(
            message=message,
            files='\n'.join([str(f) for f in self.project.files()]),
        )
        return self.completion(
            [
                dict(
                    role='user',
                    content=PROMPT,
                ),
            ],
        )

    def dependencies_refine_parse(self, response):
       return dict(files=self.list_parse(response))

    def dependencies_prompt(self, message, files):
        # ensure dependencies are in context
        files = self.context.files(*files)

        PROMPT = textwrap.dedent('''
        You are called from an automated AI assistant required to produce a
        structured response that is easily parseable by another program.

        You are given a list of files from the project and must produce the
        list of dependencies.

        {files}

        Reply ONLY with the list of dependencies in the format:
        - dependency1
        - dependency2
        ''').format(
            message=message,
            files=self.context_files_dump(),
        )
        return self.completion(
            [
                dict(
                    role='user',
                    content=PROMPT,
                ),
            ],
        )

    def dependencies_parse(self, response):
        return dict(dependencies=self.list_parse(response))
