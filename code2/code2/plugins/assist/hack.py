from code2.plugins.assist.analyze import Analyze


class Hack(Analyze):
    async def run(self, message):
        """
        Ask AI to code for you.

        We're going to split your request into an orchestrated series of
        LLM requests.

        Example:

            code2 hack refactor my Foo.bar method

        Keep it mind you can open an editor for your CLI with CTRL+X CTRL+E in bash.
        """
        msghash = self.hash(message)
        self.context.save(f'{msghash}_prompt', message)

        direction = self.process('direction', message)

        analysis = self.process(
            'analyze',
            message,
            symbols=direction.get('symbols', [])
        )
        self.print_markdown(analysis)

    def hack_prompt(self, message, symbols):
        # ok that's going to be a bit python specific
        symbols = [s for s in symbols if not s.startswith('__')]

        placeholders = ', '.join(['?'] * len(symbols))
        result = self.project.symbols(
            f's.type = "class" and s.name in ({placeholders})',
            symbols,
        )
        class_files = [row[0] for row in result]

        files = {row[0] for row in result}

        dump = []
        for file in files:
            with open(file, 'r') as f:
                dump.append(f'\n\n{file} source code:\n{f.read()}')

        PROMPT = textwrap.dedent('''
You are a coding assistant that helps with programming tasks.

First, understand if the user wants a code change or a code analysis, don't suggest a code change unless the user explicitely wants a code analysis.

To communicate with the user, explain operations, or ask questions, always use markdown format here, never put multiline content in a list, always use markdown titles.

Every code change suggestion MUST be presented as unified diff with line numbers (e.g. @@ -start,count +start,count @@), using --- for original and +++ for modified lines, and - / + to mark removals and deletions.

Never truncate, shorten, or summarize the content in unified diff, you MUST provide the full unified diff.

Never provide commands to apply the diff, the assistant knows how to do it already.

Never provide diff suggestions to files you DO NOT KNOW the content.

Always try to suggest running a test in verbose mode after changing code with a ```bash section, when suggesting a test, check the file list to find the test framework in use

Every shell command to execute MUST be wrapped between ```bash and ``` tokens so that the assistant can suggest to the user to run them.
        Your are a programming expert analyzing a problem for a pair.

        My request is:
        {message}

        My source code is:
        {files}

        Reply in markdown format.
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
