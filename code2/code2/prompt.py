import cli2
import functools
import os


class Prompt:
    def __init__(self, name):
        self.name = name

    @functools.cached_property
    def env_name(self):
        return f'PROMPT_{self.name.upper()}'

    def value(self):
        if self.env_name in os.environ:
            value = os.getenv(self.env_name)
            cli2.log.debug('prompt from env', name=self.name, value=value)

        if os.path.exists(value):
            with open(value, 'r') as f:
                value = self.read()
            cli2.log.debug('prompt from file', name=self.name, value=value)

        return value
