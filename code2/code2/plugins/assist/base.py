import cli2
import functools
import hashlib
import re
import textwrap

from litellm import completion

cli2.cfg.defaults.update(
    MODEL='openrouter/deepseek/deepseek-chat max_tokens=16384 temperature=.7 top_p=.9',  # noqa
)


class AssistPlugin:
    def __init__(self, project, context):
        self.project = project
        self.context = context

    @classmethod
    async def run_plugin(cls, name, project, context, *message, _cli2=None):
        if not message:
            return _cli2[plugin.name].help()
        obj = cls(project, context)
        return await obj.run(' '.join(message))

    @functools.cached_property
    def model_name(self):
        return cli2.cfg['MODEL'].split()[0]

    @functools.cached_property
    def model_kwargs(self):
        parts = cli2.cfg['MODEL'].split()
        kwargs = dict()
        for token in parts[1:]:
            key, value = token.split('=')
            try:
                value = int(value)
            except ValueError:
                try:
                    value = float(value)
                except ValueError:
                    pass
            kwargs[key] = value
        return kwargs

    def llm(self, messages):
        tokens = sum([len(msg['content']) for msg in messages])
        cli2.log.debug('messages', tokens=tokens, json=messages)

        stream = completion(
            messages=messages,
            stream=True,
            model=self.model_name,
            **self.model_kwargs,
        )

        full_content = ""
        for chunk in stream:
            if hasattr(chunk, 'choices') and chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content is not None:
                    full_content += delta.content

        cli2.log.debug('answer', content=full_content)
        return full_content

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
        return self.llm(
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
        return self.llm(
            [
                dict(
                    role='user',
                    content=PROMPT,
                ),
            ],
        )

    def dependencies_parse(self, response):
        return dict(dependencies=self.list_parse(response))
