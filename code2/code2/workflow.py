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
from code2 import project


class WorkflowPlugin:
    def __init__(self, project, context):
        self.project = project
        self.context = context
        self.llm_plugins = dict()

    @classmethod
    async def run_plugin(cls, context='default', *message, _cli2=None):
        message = ''
        # this is just a CLI wrapper
        if context in project.contexts:
            context = project.contexts[context]
            if context.prompt_text:
                message = [context.prompt_text]
        elif context:
            return _cli2.help(error=textwrap.dedent(f'''
            Context not found: {context}

            {cli2.t.green.bold}SOLUTION{cli2.t.rs}:
            Create a new context with: code2 edit {context}
            And type what you want to acheive in there.
            '''))

        if not context.prompt_text:
            if message:
                with context.prompt_path.open('w') as f:
                    f.write(' '.join(message))
            else:
                return _cli2.help(
                    error=textwrap.dedent(f'''
                        - No massage passed on the CLI
                        - And prompt is empty

                        {cli2.t.green.bold}SOLUTION{cli2.t.rs}:
                        - Type a prompt with command: code2 edit
                        - Or pass something in the CLI
                    '''),
                )
        obj = cls(project, context)
        return await obj.run(' '.join(message))


