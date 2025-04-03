import asyncio
import cli2
import os
import tempfile
import subprocess
import difflib
from prompt_toolkit import PromptSession
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.completion import PathCompleter
from prompt_toolkit.patch_stdout import patch_stdout
from pygments.lexers.python import PythonLexer

from code2.parser import Parser

def count_tokens(text: str) -> int:
    return len(text.split()) + len(text) // 4

async def simulate_llm_response(prompt: str) -> str:
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
    def __init__(self, project=None):
        self.project = project
        self.context = dict()
        self.multiline_mode = False
        self.test_command = None

        self.bindings = KeyBindings()

        @self.bindings.add('c-d')
        def _(event):
            print('Goodbye!')
            event.app.exit()

        @self.bindings.add('c-l')
        def _(event):
            clear()

        @self.bindings.add('c-x', 'c-e')
        def _(event):
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

        history_file = os.path.expanduser('~/.code2_history')
        self.session = PromptSession(
            lexer=PygmentsLexer(PythonLexer),
            history=FileHistory(history_file),
            message='code2> ',
            key_bindings=self.bindings,
            completer=PathCompleter(expanduser=True),
            bottom_toolbar='[Ctrl+D] exit, [Ctrl+L] clear, [Ctrl+X Ctrl+E] vim',
            multiline=False,
            complete_while_typing=True,
            complete_in_thread=True
        )

    async def confirm_action(self, message: str, diff: str = None) -> bool:
        if diff:
            print('Proposed changes:')
            cli2.diff(diff)
        answer = await self.session.prompt_async(f'{message} (y/n): ')
        return answer.strip().lower() in ('y', 'yes')

    async def run_command(self, command: str):
        process = await asyncio.create_subprocess_exec(
            *command.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT  # merge stderr into stdout
        )

        output = []

        # Read line by line
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            decoded_line = line.decode().rstrip()
            print(decoded_line)  # Live output to user
            output.append(decoded_line)

        await process.wait()

        output = "\n".join(output)
        print(output)
        tokens = count_tokens(output)
        if await self.confirm_action(f"Add output to context? ({tokens} tokens)"):
            self.context[f"Command output: {op['command']}"] = output

        return process.returncode

    async def cmd_exit(self, cmd_parts):
        print('Goodbye!')
        return True

    async def cmd_help(self, cmd_parts):
        help_text = """
Available commands:
/add <files...> - Add files to context
/exit or /quit - Exit the assistant
/help - Show this help
/run <command> - Run a shell command
/multiline-mode - Toggle multiline mode
/paste - Paste from clipboard
/scan - Print scanning message
/test [command] - Set/run test command
        """
        print(help_text)

    async def cmd_add(self, cmd_parts):
        if len(cmd_parts) < 2:
            print('Please specify files to add')
        else:
            for file_path in cmd_parts[1:]:
                await self.file_add(file_path)

    async def file_add(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
                tokens = count_tokens(content)
                self.context[f"File: {file_path}"] = content
                print(f'Added {file_path} ({tokens} tokens)')
        else:
            print(f'File not found: {file_path}')

    async def cmd_run(self, cmd_parts):
        if len(cmd_parts) < 2:
            print('Please specify a command')
        else:
            command = ' '.join(cmd_parts[1:])
            await self.run_command(command)

    async def cmd_multiline_mode(self, cmd_parts):
        self.multiline_mode = not self.multiline_mode
        self.session.multiline = self.multiline_mode
        state = "enabled" if self.multiline_mode else "disabled"
        print(f'Multiline mode {state}')

    async def cmd_paste(self, cmd_parts):
        try:
            output = subprocess.check_output(['xclip', '-o', '-selection', 'clipboard']).decode()
        except:
            try:
                output = subprocess.check_output(['wl-paste']).decode()
            except:
                output = "Clipboard access failed"
                print(output)
                return
        print(output)
        tokens = count_tokens(output)
        if await self.confirm_action(f"Add clipboard content to context? ({tokens} tokens)"):
            self.context["Pasted content"] = output

    async def cmd_scan(self, cmd_parts):
        print('scanning')

    async def cmd_test(self, cmd_parts):
        if len(cmd_parts) > 1:
            self.test_command = ' '.join(cmd_parts[1:])
            print(f'Test command set: {self.test_command}')
        elif self.test_command:
            rc = await self.run_command(self.test_command)
            print(output)
            tokens = count_tokens(output)
            if await self.confirm_action(f"Add test output to context? ({tokens} tokens)"):
                self.context[f"Command output: {self.test_command}"] = output
        else:
            print('No test command set')

    async def handle_command(self, user_input: str) -> bool:
        if user_input.startswith('/'):
            cmd_parts = user_input[1:].split()
            cmd = cmd_parts[0].lower()

            commands = {
                'exit': self.cmd_exit,
                'quit': self.cmd_exit,
                'help': self.cmd_help,
                'add': self.cmd_add,
                'run': self.cmd_run,
                'multiline-mode': self.cmd_multiline_mode,
                'paste': self.cmd_paste,
                'scan': self.cmd_scan,
                'test': self.cmd_test
            }

            if cmd in commands:
                await commands[cmd](cmd_parts)
                return cmd in ('exit', 'quit')
        return False

    async def run(self, callback):
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
        user_input = await self.session.prompt_async()
        if not user_input or not user_input.strip():
            return

        for token in user_input.split():
            if token in ('.', '..'):
                continue

            if os.path.exists(token):
                if await self.confirm_action(f"Add {token} to context?"):
                    await self.file_add(token)

        if await self.handle_command(user_input):
            return

        for key, value in self.context.items():
            user_input += f'\n\n{key}:\n{value}'

        operations = await callback(user_input)
        for op in operations:
            if op['type'] == 'talk':
                print(op["content"])
            elif op['type'] == 'run':
                print(f'+ {op["command"]}')
                if await self.confirm_action(f"Execute command?"):
                    rc = await self.run_command(op['command'])
            elif op['type'] == 'code':
                print(f'Change {op["file_path"]}')
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
