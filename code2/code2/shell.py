# code2.py
import asyncio
import cli2
import os
import tempfile
import subprocess
import difflib
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit import print_formatted_text
from pygments import highlight
from pygments.lexers.python import PythonLexer
from pygments.formatters import TerminalFormatter

from code2.parser import Parser

async def simulate_llm_response(prompt: str) -> str:
    """Simulate an LLM response for demonstration."""
    data = f"""
[TALK]
Processing your request: {prompt}
[/TALK]

[CODE]
example.py
~~~before
print("Old")
~~~
~~~after
def hello():
    print("Hello, World!")
~~~
[/CODE]

[RUN]
python -m unittest example.py
[/RUN]
    """
    return Parser().parse(data)


class Shell:
    def __init__(self):
        # Custom style for the prompt
        self.style = Style.from_dict({
            'prompt': '#ansigreen bold',
            'talk': '#ansiblue',
            'run': '#ansiyellow',
            'code': '#ansimagenta',
            'filepath': '#ansicyan',
            'before': '#ansired',
            'after': '#ansigreen',
        })

        # Key bindings
        self.bindings = KeyBindings()

        @self.bindings.add('c-d')
        def _(event):
            """Exit with Ctrl+D"""
            event.app.exit()

        @self.bindings.add('c-l')
        def _(event):
            """Clear screen with Ctrl+L"""
            clear()

        @self.bindings.add('c-x', 'c-e')
        def _(event):
            """Open vim with Ctrl+X Ctrl+E"""
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tmp:
                tmp_name = tmp.name
                try:
                    subprocess.call(['vim', tmp_name])
                    with open(tmp_name, 'r') as f:
                        content = f.read().strip()
                    if content:
                        event.app.current_buffer.text = content
                        event.app.current_buffer.cursor_position = len(content)
                finally:
                    os.unlink(tmp_name)

        # Create prompt session
        history_file = os.path.expanduser('~/.code2_history')
        self.session = PromptSession(
            lexer=PygmentsLexer(PythonLexer),
            history=FileHistory(history_file),
            message=HTML('<prompt>code2> </prompt>'),
            style=self.style,
            key_bindings=self.bindings,
            bottom_toolbar=HTML('<b>[Ctrl+D]</b> exit, <b>[Ctrl+L]</b> clear, <b>[Ctrl+X Ctrl+E]</b> vim'),
        )

    async def confirm_action(self, message: str, diff: str = None) -> bool:
        """Ask user for confirmation using the session's prompt, optionally showing a diff."""
        if diff:
            print_formatted_text(HTML('<talk>Proposed changes:</talk>'), style=self.style)
            cli2.diff(diff)
        answer = await self.session.prompt_async(
            HTML(f'<prompt>{message} (y/n): </prompt>')
        )
        return answer.strip().lower() in ('y', 'yes')

    async def run_command(self, command: str):
        """Execute a shell command and return output."""
        process = await asyncio.create_subprocess_exec(
            *command.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        return stdout.decode() + stderr.decode()

    async def run(self, callback):
        """Main loop for the assistant."""
        while True:
            try:
                await self.run_once(callback)
            except KeyboardInterrupt:
                return
            except EOFError:
                break
            except Exception as e:
                cli2.log.exception()

    async def run_once(self, callback):
        # Get user input
        user_input = await self.session.prompt_async()
        if not user_input or not user_input.strip():
            return

        # Simulate LLM response
        operations = await callback(user_input)

        # Display and execute operations with confirmation
        for op in operations:
            if op['type'] == 'talk':
                print_formatted_text(
                    HTML(f'<talk>{op["content"]}</talk>'),
                    style=self.style
                )
            elif op['type'] == 'run':
                print_formatted_text(
                    HTML(f'<run>+ {op["command"]}</run>'),
                    style=self.style
                )
                if await self.confirm_action(f"Execute command?"):
                    output = await self.run_command(op['command'])
                    print(output)
            elif op['type'] == 'code':
                print_formatted_text(
                    HTML(f'<code>Change <filepath>{op["file_path"]}</filepath></code>'),
                    style=self.style
                )
                # Generate diff
                diff = difflib.unified_diff(
                    op['before'].splitlines(),
                    op['after'].splitlines(),
                    'before',
                    'after',
                )
                if await self.confirm_action(f"Write changes to '{op['file_path']}'?", diff):
                    with open(op['file_path'], 'w') as f:
                        f.write(op['after'])

if __name__ == "__main__":
    assistant = Shell()
    asyncio.run(assistant.run(simulate_llm_response))
