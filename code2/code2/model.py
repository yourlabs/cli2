"""
Juggle between multiple models by defining environment variables.

.. envvar:: MODEL

    An environment variable to configure the default LLM plugin, as far as
    the base plugin is concerned, it must be in the following format::

        [<code2 backend plugin>] [<args>...] [<kwarg=value>...]

    When the backend plugin is omited, or not found,
    :py:class:`~code2.plugins.backend.litellm` is used by default which should
    be fine in most cases, leveraging the env vars you already have say for
    aider or anything using litellm, such as ``$OPENAI_API_KEY``,
    ``$OPENROUTER_API_KEY``, etc. For the litellm backend, the first arg is the
    model name and kwargs are optional.

    The default value for MODEL env var is::

        MODEL=openrouter/google/gemini-2.5-pro-exp-03-25:free

    You can add litellm kwargs as such::

        MODEL='openrouter/deepseek/deepseek-chat:free max_tokens=16384'

.. envvar:: MODEL_name

    ``MODEL_name`` is not an actual variable, it represents other models
    configurations that you can have, ie::

        MODEL_EDITOR='deepseek/deepseek-chat:free max_tokens=16384'
        MODEL_ARCHITECT=xai/grok-2-latest

    While you will be able to use the model names you want in your own code2
    workflow plugins, code2 core prompt plugins will try to use the best one
    that is defined for a purpose based on standard names, "editor" and
    "architect" at this time.
    https://aider.chat/2024/09/26/architect.html
"""

from pathlib import Path
import cli2
import importlib.metadata
import json
import hashlib
import os


class Model:
    models = dict()

    def __init__(self, backend, *args, **kwargs):
        self.backend = backend
        self.args = args
        self.kwargs = kwargs

    @property
    def cache_path(self):
        return Path(os.getenv('HOME')) / '.code2/cache'

    @classmethod
    def get(cls, *names):
        names = list(names)
        if 'default' not in names:
            names.append('default')

        key = None
        for name in names:
            if not name:
                continue

            if name in cls.models:
                return cls.models[name]

            if name == 'default':
                key = 'MODEL'
            else:
                key = f'MODEL_{name.upper()}'

            if key in os.environ:
                break

        if key and key in os.environ:
            configuration = os.environ[key]
        else:
            # default value
            configuration = 'openrouter/deepseek/deepseek-r1:free'

        cls.models[name] = cls.factory(configuration)
        return cls.models[name]

    @classmethod
    def factory(cls, configuration):
        tokens = configuration.split()

        # load the backend plugin based on first token, litellm by default
        plugins = importlib.metadata.entry_points(
            name=tokens[0],
            group='code2_backend',
        )
        if plugins:
            tokens = tokens[1:]
            plugin = [*plugins][0].load()
        else:
            from code2.plugins.backend.litellm import LiteLLMBackend
            plugin = LiteLLMBackend

        args = list()
        kwargs = dict()
        for token in tokens:
            key = None
            if '=' in kwargs:
                key, value = token.split('=')
            else:
                value = token

            try:
                value = float(value)
            except ValueError:
                try:
                    value = int(value)
                except ValueError:
                    pass

            if key:
                kwargs[key] = value
            else:
                args.append(value)

        backend = plugin(*args, **kwargs)
        return cls(backend, *args, **kwargs)

    async def completion(self, messages, cache_key=None):
        cache_key = cache_key or self.hash(messages)
        cache_path = self.cache_path / f'{cache_key}_response.txt'

        if cache_path.exists():
            cli2.log.debug('cache hit!', cache_key=cache_key, json=messages)
            with cache_path.open('r') as f:
                return f.read()

        response = await self.backend.completion(messages)

        self.cache_path.mkdir(exist_ok=True, parents=True)
        cli2.log.debug('cached', cache_key=cache_key, response=response)
        with cache_path.open('w') as f:
            f.write(response)

        return response

    def hash(self, messages):
        _ = hashlib.new('sha1')
        cache = messages
        _.update(json.dumps(cache).encode('utf8'))
        return _.hexdigest()

    def parser_get(self, parser_name):
        plugins = importlib.metadata.entry_points(
            name=parser_name,
            group='code2_parser',
        )
        if not plugins:
            raise Exception(f'Parser {parser_name} not found')
        plugin = [*plugins][0]
        cli2.log.debug('loading parser', name=plugin.name, value=plugin.value)
        return plugin.load()(self)

    async def process(self, messages, parser=None, cache_key=None):
        if parser:
            parser = self.parser_get(parser)

        # messages quacking like a Prompt are supported
        if getattr(messages, 'messages', None):
            if callable(messages.messages):
                messages = messages.messages()

        if parser:
            parser.messages(messages)

        tokens = sum([len(msg['content']) for msg in messages])

        cli2.log.debug('messages', tokens=tokens, json=messages)
        result = await self.completion(messages)
        cli2.log.debug('response', response=result)

        if parser:
            result = parser.parse(result)
            cli2.log.debug('parsed', result=result)

        return result
