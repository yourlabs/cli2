import cli2
import functools
import hashlib
import re
import textwrap

from litellm import completion

cli2.cfg.defaults.update(
    MODEL='openrouter/deepseek/deepseek-chat max_tokens=16384 temperature=.7 top_p=.9',  # noqa
)


def print_markdown(content):
    from rich.console import Console
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    console = Console()
    md = Markdown(content)
    console.print(md)


class AssistPlugin:
    def __init__(self, project, context):
        self.project = project
        self.context = context

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
        msghash = self.hash(f'{cli2.cfg["MODEL"]} message')
        hashkey = f'{msghash}_{key}'
        response = self.context.load(hashkey)
        if not response:
            response = getattr(self, f'{key}_prompt')(message, **kwargs)
            self.context.save(hashkey, response)
        parser = getattr(self, f'{key}_parse', None)
        if parser:
            result = parser(response)
            cli2.log.info(key, **result)
            return result
        else:
            cli2.log.info(key, response=response)
            return response


class Analyze(AssistPlugin):
    async def run(self, message):
        """
        Ask AI for a code analysis.

        We're going to split your request into an orchestrated series of
        LLM requests.

        Example:

            code2 grok refactor my Foo.bar method

        Keep it mind you can open an editor for your CLI with CTRL+X CTRL+E in bash.
        """
        msghash = self.hash(message)
        self.context.save(f'{msghash}_prompt', message)

        direction = self.process('direction', message)

        if direction.get('intent', 'UNCLEAR') != 'CODE':
            analysis = self.process(
                'analyze',
                message,
                symbols=direction.get('symbols', [])
            )
            print_markdown(analysis)

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

        dump = []
        for file in files:
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


class Old:
    def direction_prompt(self, message):
        PROMPT = textwrap.dedent('''
        You are a programming AI assistant.

        The user made this request:
        {message}

        First, determine I want to change code or just an analysis.
        Reply with "CODE" if they want code changes, "ANALYZE" if they want an
        explanation or analysis, or "UNCLEAR" if the intent is ambiguous.

        If the intent is "CODE" or "ANALYZE", also list the relevant symbols from the
        following dump of symbols in the code directory:
        {symbols}


        Reply in the format:
        Intent: CODE
        Symbols:
        - symbol1
        - symbol2
        Or
        Intent: ANALYZE
        Symbols:
        - symbol1
        - symbol2
        Or
        Intent: UNCLEAR
        Reason: <brief explanation>
        Symbols:
        - symbol1
        - symbol2
        ''').format(
            message=message,
            symbols='\n'.join([row[3] for row in self.project.symbols()]),
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
        lines = response.strip().splitlines()

        result = {
            "intent": None,
            "symbols": [],
            "reason": None
        }

        current_section = None
        reason_lines = []

        for line in lines:
            line = line.rstrip()  # Remove trailing whitespace

            # Intent line
            if line.startswith("Intent:"):
                result["intent"] = line[len("Intent:"):].strip()
                current_section = None

            # symbols section start
            elif line.strip() == "Symbols:":
                current_section = "symbols"

            # Reason section start
            elif line.startswith("Reason:"):
                current_section = "reason"
                reason_lines.append(line[len("Reason:"):].strip())

            # Handle indented or list items in symbols section
            elif current_section == "symbols" and line.strip().startswith("-"):
                file_path = line.strip()[1:].strip()  # Remove "- " and extra spaces
                if file_path:
                    result["symbols"].append(file_path)

            # Accumulate Reason text
            elif current_section == "reason" and line.strip():
                reason_lines.append(line.strip())

        # Join reason lines into a single string
        if reason_lines:
            result["reason"] = " ".join(reason_lines)

        return result


class Old:
    def direction_prompt(self, message):
        PROMPT = textwrap.dedent('''
        You are a programming AI assistant.

        The user made this request:
        {message}

        First, determine I want to change code or just an analysis.
        Reply with "CODE" if they want code changes, "ANALYZE" if they want an
        explanation or analysis, or "UNCLEAR" if the intent is ambiguous.

        If the intent is "CODE" or "ANALYZE", also list the relevant symbols from the
        following dump of symbols in the code directory:
        {symbols}


        Reply in the format:
        Intent: CODE
        Symbols:
        - symbol1
        - symbol2
        Or
        Intent: ANALYZE
        Symbols:
        - symbol1
        - symbol2
        Or
        Intent: UNCLEAR
        Reason: <brief explanation>
        Symbols:
        - symbol1
        - symbol2
        ''').format(
            message=message,
            symbols='\n'.join([row[3] for row in self.project.symbols()]),
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
        lines = response.strip().splitlines()

        result = {
            "intent": None,
            "symbols": [],
            "reason": None
        }

        current_section = None
        reason_lines = []

        for line in lines:
            line = line.rstrip()  # Remove trailing whitespace

            # Intent line
            if line.startswith("Intent:"):
                result["intent"] = line[len("Intent:"):].strip()
                current_section = None

            # symbols section start
            elif line.strip() == "Symbols:":
                current_section = "symbols"

            # Reason section start
            elif line.startswith("Reason:"):
                current_section = "reason"
                reason_lines.append(line[len("Reason:"):].strip())

            # Handle indented or list items in symbols section
            elif current_section == "symbols" and line.strip().startswith("-"):
                file_path = line.strip()[1:].strip()  # Remove "- " and extra spaces
                if file_path:
                    result["symbols"].append(file_path)

            # Accumulate Reason text
            elif current_section == "reason" and line.strip():
                reason_lines.append(line.strip())

        # Join reason lines into a single string
        if reason_lines:
            result["reason"] = " ".join(reason_lines)

        return result
