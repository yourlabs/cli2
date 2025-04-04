"""
Base Assistant plugin which you can inherit from.

Plugins register themselves over the ``code2_assist`` entrypoint, and are
exposed on the command line for every context.

To create your own plugin, create a Python package with an entrypoint like:

.. code-block:: python

    'code2_assist': [
        'plugin_name = your.module:ClassName',
    ]

Install the package and ``plugin_name`` will appear in the code2 command line.
"""

import cli2
import functools
import importlib.metadata
import hashlib
import re
import textwrap


class AssistPlugin:
    def __init__(self, project, context):
        self.project = project
        self.context = context
        self.llm_plugins = dict()

    @classmethod
    async def run_plugin(cls, name, project, context, *message, _cli2=None):
        if not message:
            return _cli2[plugin.name].help()
        obj = cls(project, context)
        return await obj.run(' '.join(message))

    def hash(self, message):
        _ = hashlib.new('sha1')
        _.update(message.encode('utf8'))
        return _.hexdigest()

    def process(self, key, message, **kwargs):
        print(f'{key} processing ...')
        msghash = self.hash(f'{cli2.cfg["MODEL"]} {message}')
        hashkey = f'{msghash}_{key}'
        response = self.context.load(hashkey)
        if not response:
            response = getattr(self, f'{key}_prompt')(message, **kwargs)
            self.context.save(hashkey, response)
        else:
            print('cache hit!')
        parser = getattr(self, f'{key}_parse', None)
        if parser:
            result = parser(response)
            cli2.log.info(key, **result)
            return result
        else:
            cli2.log.info(key, response=response)
            return response

    def list_parse(self, response):
        results = []
        for line in response.splitlines():
            match = re.match('^- (.*)$', line)
            if match:
                results.append(match.group(1).strip())
        return results

    def print_markdown(self, content):
        # TODO: this has to move in cli2.display
        from rich.console import Console
        from rich.syntax import Syntax
        from rich.markdown import Markdown
        console = Console()
        md = Markdown(content)
        console.print(md)

    def choice(self, question, choices=None, default=None):
        choices = [c.lower() for c in choices or ['y', 'n']]

        if default:
            choices_display = [
                c.upper() if c == default.lower() else c
                for c in choices
            ]
        else:
            choices_display = choices

        question = question + f' ({"/".join(choices_display)})'

        while answer := input(question):
            if not answer and default:
                return default
            if answer.lower() in choices:
                return answer.lower()

    def completion(self, messages, models=None):
        """
        Request completion for a list of messages.

        messages looks like this:

        .. code-block:: python

            messages = [
                dict(role="user", content=user_message),
            ]

            # can also contain more:
            messages = [
                dict(role="system", content=your_system_prompt),
                dict(role="user", content=previous_message),
                dict(role="assistant", content=previous_assistant_reply),
                dict(role="user", content=user_message),
            ]

        ``models`` is optionnal, and by default will be ``['default']``.
        ``'default'`` will always be appended to the list.

        Default model is configured by the :envvar:`MODEL` environment
        variable, but can be used to change models based on the kind of
        completion you want.

        You can specify other models for your plugin to use in a
        ``MODEL_$name`` environment variable. For example, if
        :envvar:``MODEL_ARCHITECT`` is defined, then this method will use that
        variable instead of :envvar:`MODEL` if the ``models`` argument is:
        ``['architect']``. Refer to :envvar:`MODEL_OTHER` for more.

        :param message: List of message dicts, each containing at least a
                        ``content`` key, can have a ``role`` key, typically in
                        "user", "assistant", "system"...
        :param models: List of model names, the first one found will be used,
                       "default" will be appendend to this list so that
        """

        if not models:
            models = []
        if 'default' not in models:
            models.append('default')

        for model in models:
            if model in self.llm_plugins:
                break

            # load the model configuration, MODEL by default
            if model == 'default':
                plugin_conf = cli2.cfg['MODEL']
            else:
                model_var = f'MODEL_{model.upper()}'
                if model_var in os.environ:
                    plugin_conf = os.environ[model_var]
                else:
                    continue

            tokens = plugin_conf.split()

            # load the plugin based on first token, litellm by default
            plugins = importlib.metadata.entry_points(
                name=tokens[0],
                group='code2_llm',
            )
            if plugins:
                model_conf = tokens[1:]
                plugin = plugins[0]
            else:
                model_conf = tokens
                plugin = [*importlib.metadata.entry_points(
                    name='litellm',
                    group='code2_llm',
                )][0]

            self.llm_plugins[model] = plugin.load().factory(*model_conf)
            break

        tokens = sum([len(msg['content']) for msg in messages])
        cli2.log.debug('messages', tokens=tokens, json=messages)
        content = self.llm_plugins[model].completion(messages)
        cli2.log.debug('answer', content=content)
        return content

    def dependencies_refine_prompt(self, message):
        PROMPT = textwrap.dedent('''
        You are called from an automated AI assistant requiring a structured
        response.

        You are given a list of files in a project and find any file that could
        give clues about the used dependencies.

        {files}

        Reply ONLY with the list of languages and files in the format:
        - file1
        - file2
        ''').format(
            message=message,
            files='\n'.join(self.project.files()),
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
        dump = []
        for file in files:
            if self.choice(f'Add {file} to context?') != 'y':
                continue
            with open(file, 'r') as f:
                dump.append(f'\n\n{file} source code:\n{f.read()}')

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
            files=dump,
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
