import textwrap
import re

from code2.workflow import WorkflowPlugin
from code2.prompt import Prompt


class AnalyzeWorkflow(WorkflowPlugin):
    async def run(self, *message, _cli2=None):
        """
        Ask AI for a code analysis.

        We're going to split your request into an orchestrated series of
        LLM requests.

        Example:

            code2 analyze why is my widget always hidden

        Keep it mind you can open an editor for your CLI with CTRL+X CTRL+E in bash.

        :param message: Your message to the AI
        """
        if not message:
            return _cli2.help(error='message is required')

        architect = Prompt('architect')
        request = prompt_read('directions').format(
            message=message,
            symbols=symbols,
        )

        msghash = self.hash(message)
        self.context.save(f'{msghash}_prompt', message)

        direction = self.process('direction', message)

        analysis = self.process(
            'analyze',
            message,
            symbols=direction.get('symbols', [])
        )
        self.print_markdown(analysis)

    def direction_prompt(self, message):
        PROMPT = textwrap.dedent('''
        You are my programming AI assistant.

        I want you to run an analysis on my code, this is my request:
        {message}

        List of symbols I have in my code:
        {symbols}

        What symbols are you interested in to fullfill my request?
        Reply ONLY with the list of symbols in the format:
        - symbol1
        - symbol2
        ''').format(
            message=message,
            symbols='\n'.join(self.project.symbols_unique()),
        )
        return self.completion(
            [
                dict(
                    role='user',
                    content=PROMPT,
                ),
            ],
        )

    def direction_parse(self, response):
        symbols = []
        for line in response.splitlines():
            match = re.match('^- (\\w+)$', line)
            if match:
                symbols.append(match.group(1).strip())
        return dict(symbols=symbols)

    def analyze_prompt(self, message, symbols):
        # TODO: remove python-specific symbol refinment here
        # the first goal of code2 is to write itself so I don't mind starting
        # with just python
        symbols = [s for s in symbols if not s.startswith('__')]

        placeholders = ', '.join(['?'] * len(symbols))
        result = self.project.symbols(
            f's.type = "class" and s.name in ({placeholders})',
            symbols,
        )
        class_files = [row[0] for row in result]

        files = {row[0] for row in result}

        if not files:
            print(
                'It is unclear what code you are talking about'
                ', perhaps run code2 project scan and try again?'
            )
            return

        self.context.files(*files)

        PROMPT = textwrap.dedent('''
        Your are a programming expert analyzing a problem for a pair.

        My request is:
        {message}

        My source code is:
        {files}

        Provide a concise explanation or analysis in markdown format.
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
