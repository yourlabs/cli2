import textwrap

from code2.plugins.assist.base import AssistPlugin


class Ask(AssistPlugin):
    async def run(self, message):
        """
        Ask AI a general question.

        We'll help the AI figure what programing language and dependencies you
        are using so that it can orient its anwser.

        Example:

            code2 ask how to create a new cli command

        In cli2 repository, it should answer with cli2.

        Keep it mind you can open an editor for your CLI with CTRL+X CTRL+E in bash.
        """
        msghash = self.hash(message)
        self.context.save(f'{msghash}_prompt', message)

        files = self.process('dependencies_refine', message)
        dependencies = self.process('dependencies', message, files=files['files'])

        answer = self.process(
            'ask',
            message,
            dependencies=dependencies['dependencies'],
        )
        self.print_markdown(answer)

    def ask_prompt(self, message, dependencies):
        PROMPT = textwrap.dedent('''
        You are my programming AI senior pair programer asked a general
        question about a project:
        {message}

        These are the current dependencies for the project:
        {dependencies}

        Reply in markdown format.
        ''').format(
            message=message,
            dependencies='\n'.join(dependencies),
        )
        return self.llm(
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
        # ok that's going to be a bit python specific
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

        dump = []
        for file in files:
            if self.choice(f'Add {file} to context?') != 'y':
                continue
            with open(file, 'r') as f:
                dump.append(f'\n\n{file} source code:\n{f.read()}')

        PROMPT = textwrap.dedent('''
        Your are a programming expert analyzing a problem for a pair.

        My request is:
        {message}

        My source code is:
        {files}

        Provide a concise explanation or analysis in markdown format.
        ''').format(
            message=message,
            files='\n'.join(dump),
        )
        return self.llm(
            [
                dict(
                    role='user',
                    content=PROMPT,
                ),
            ],
        )
