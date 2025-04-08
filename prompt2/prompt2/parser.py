import cli2
import importlib.metadata

from .exception import NotFoundError


class Parser:
    entry_point = 'prompt2_parser'
    system = None

    class NotFoundError(NotFoundError):
        title = 'PARSER NOT FOUND'

        def available_list(self):
            plugins = importlib.metadata.entry_points(
                group=Parser.entry_point,
            )
            return [p.name for p in plugins]

    def __init__(self, model):
        self.model = model

    @classmethod
    def get(cls, name):
        plugins = importlib.metadata.entry_points(
            name=name,
            group=Parser.entry_point,
        )
        if not plugins:
            raise cls.NotFoundError(name)
        return [*plugins][0].load()

    def messages(self, messages):
        if self.system:
            messages.append(
                dict(
                    role='system',
                    content=self.system,
                ),
            )
        return messages

    def parse(self, response):
        return response


class Wholefile(Parser):
    system = "Respond only with the complete new file content, as this will be directly written to the file by an automated AI assistant tool—no additional text, comments, or explanations are allowed."  # noqa

    def parse(self, response):
        if response.startswith('```'):
            # strip markup the IA absolutely wants to add
            return '\n'.join([l for l in response.split('\n')[1:-1]])
        return response


class List(Parser):
    system = "Respond only with the requested list because it will be processed by an automated AI assistant tool—no additional text, comments, or explanations are allowed."  # noqa

    def parse(self, response):
        breakpoint()
        return response
