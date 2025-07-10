import importlib.metadata
import re

from cli2.exceptions import NotFoundError


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
            return '\n'.join([
                line for line in response.split('\n')[1:-1]
            ])
        return response


class List(Parser):
    system = """
Provide your response as a list in the following format, with each item on a new line preceded by a hyphen and a space. Include only the item names, with no additional text, descriptions, or annotations:

- item1
- item2
    """  # noqa

    def parse(self, response):
        if response.startswith('```'):
            # strip markup the IA absolutely wants to add
            response = '\n'.join([
                line for line in response.split('\n')[1:-1]
            ])
        if response.strip().startswith('-'):
            result = []
            for line in response.splitlines():
                if match := re.match('^- (.*)', line):
                    for item in match.group(1).split('- '):
                        result.append(item.strip())
            result = list(set(result))
            return result
        return response
