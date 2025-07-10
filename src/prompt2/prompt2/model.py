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

from cli2.exceptions import NotFoundError
from .plugins.litellm import LiteLLMPlugin
from .parser import Parser
from .plugin import Plugin


class Model:
    default = 'openrouter/deepseek/deepseek-r1:free'

    class NotFoundError(NotFoundError):
        title = 'MODEL NOT FOUND'

        def available_list(self):
            models = {
                key[6:].lower(): os.environ[key]
                for key in os.environ
                if key.startswith('MODEL_')
            }
            models['default'] = os.getenv('MODEL', Model.default)
            return models

    def __init__(self, backend=None):
        if not isinstance(backend, Plugin):
            configuration = self.configuration_get(backend or '')
            backend = self.backend_factory(configuration)
        self.backend = backend
        self._cache_path = None

    @property
    def cache_path(self):
        if not self._cache_path:
            if 'PROMPT2_CACHE_PATH' in os.environ:
                self._cache_path = Path(os.getenv('PROMPT2_CACHE_PATH'))
            else:
                self._cache_path = Path(os.getenv('HOME')) / '.code2/cache'
        return self._cache_path

    @cache_path.setter
    def cache_path(self, value):
        self._cache_path = value

    @classmethod
    def configuration_get(cls, name, strict=False):
        if not isinstance(name, (tuple, list, set)):
            name = [name]

        keys = [
            f'MODEL_{name.upper()}'
            for name in name
        ]

        key = None
        for _ in keys:
            if _ in os.environ:
                key = _
                break

        if not key:
            if strict:
                raise cls.NotFoundError(', '.join(name))
            if 'MODEL' in os.environ:
                key = 'MODEL'

        if key and key in os.environ:
            configuration = os.environ[key]
        else:
            # default value
            configuration = cls.default

        return configuration

    @staticmethod
    def configuration_parse(tokens):
        args = list()
        kwargs = dict()
        for token in tokens:
            key = None
            if '=' in token:
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
        return args, kwargs

    @classmethod
    def backend_factory(cls, configuration):
        tokens = configuration.split()

        # load the backend plugin based on first token, litellm by default
        plugins = importlib.metadata.entry_points(
            name=tokens[0],
            group='prompt2',
        )
        if plugins:
            tokens = tokens[1:]
            plugin = [*plugins][0].load()
        else:
            plugin = LiteLLMPlugin

        args, kwargs = cls.configuration_parse(tokens)

        return plugin(*args, **kwargs)

    async def completion(self, messages, cache_key=None, stream=False):
        cache_key = cache_key or self.hash(
            messages + [str(self.backend)]
        )
        cache_path = self.cache_path / f'{cache_key}_response.txt'

        if cache_path.exists():
            cli2.log.debug('cache hit!', cache_path=cache_path, json=messages)
            with cache_path.open('r') as f:
                content = f.read()
            if stream:
                print(cli2.highlight(content, 'Markdown'))
            return content

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

    def parser(self, name):
        return Parser.get(name)(self)

    async def process(self, messages, parser=None, cache_key=None,
                      stream=False):
        if parser:
            messages = parser.messages(messages)

        tokens = sum([len(msg['content']) for msg in messages])
        cli2.log.debug('messages', tokens=tokens, json=messages)
        result = await self.completion(messages, stream=stream)
        cli2.log.debug('response', response=result)

        if parser:
            result = parser.parse(result)
            cli2.log.debug('parsed', result=result)

            class ParserResult(type(result)):
                pass

            _result = ParserResult(result)
            # attach parser and actual result
            _result.parser = parser
            _result.result = result
            result = _result
        return result

    async def __call__(self, messages, parser=None, cache_key=None,
                       stream=True):
        if isinstance(parser, str):
            # load parser object from string
            parser = self.parser(parser)

        if callable(getattr(messages, 'messages', None)):
            # quacks like a Prompt object
            messages = await messages.messages()

        return await self.process(messages, parser, cache_key=cache_key,
                                  stream=stream)

    def __str__(self):
        return str(self.backend)
