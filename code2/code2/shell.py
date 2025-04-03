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


class Abort(Exception):
    pass


def count_tokens(text: str) -> int:
    return len(text.split()) + len(text) // 4


class Shell:
    def __init__(self, project=None):
        self.project = project
        self.context = dict()
        self.multiline_mode = False
        self.test_command = None

        self.bindings = KeyBindings()

        @self.bindings.add("c-d")
        def _(event):
            print("Goodbye!")
            event.app.exit()
            self.keep_running = False

        @self.bindings.add("c-l")
        def _(event):
            clear()

        @self.bindings.add("c-x", "c-e")
        def _(event):
            with tempfile.NamedTemporaryFile(
                mode="w+", suffix=".txt", delete=False
            ) as tmp:
                tmp_name = tmp.name
                try:
                    subprocess.call(["vim", tmp_name])
                    with open(tmp_name, "r") as f:
                        content = f.read().strip()
                    if content:
                        event.app.current_buffer.text = content
                        event.app.current_buffer.cursor_position = len(content)
                finally:
                    os.unlink(tmp_name)

        class CommandCompleter(Completer):
            def __init__(self):
                self.path_completer = PathCompleter(expanduser=True)
                self.commands = {
                    'add': None,
                    'exit': None,
                    'help': None,
                    'multiline-mode': None,
                    'paste': None,
                    'quit': None,
                    'run': None,
                    'scan': None,
                    'test': None,
                }

            def get_completions(self, document, complete_event):
                text = document.text_before_cursor.lstrip()

                # Complete commands if text starts with /
                if text.startswith('/'):
                    try:
                        cmd_part = text[1:].split()[0].lower()
                    except IndexError:
                        cmd_part = ''
                    for cmd in self.commands:
                        if cmd.startswith(cmd_part):
                            start_pos = -len(cmd_part) if cmd_part else 0
                            yield Completion(f'/{cmd}', start_position=start_pos)
                # Otherwise complete paths
                else:
                    yield from self.path_completer.get_completions(document, complete_event)

        history_file = os.path.expanduser("~/.code2_history")
        self.session = PromptSession(
            lexer=PygmentsLexer(PythonLexer),
            history=FileHistory(history_file),
            message="code2> ",
            key_bindings=self.bindings,
            completer=PathCompleter(expanduser=True),
            bottom_toolbar="[Ctrl+D] exit, [Ctrl+L] clear, [Ctrl+X Ctrl+E] vim",
            multiline=False,
            complete_while_typing=True,
            complete_in_thread=True,
        )

    async def confirm_action(self, message: str, diff: str = None) -> bool:
        if diff:
            print("Proposed changes:")
            cli2.diff(diff)
        while answer := await self.session.prompt_async(f"{message} (y/n): "):
            if answer.strip().lower() in ("y", "yes"):
                return True
            elif answer.strip().lower() in ('n', 'no'):
                return False

    async def run_command(self, command: str):
        if not await self.confirm_action(f"Execute command {command}?"):
            return

        process = await asyncio.create_subprocess_exec(
            *command.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,  # merge stderr into stdout
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
        print("Goodbye!")
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
            print("Please specify files to add")
        else:
            for file_path in cmd_parts[1:]:
                await self.file_add(file_path)

    async def file_add(self, file_path):
        if os.path.exists(file_path):
            if await self.confirm_action(f"Add {file_path} to context?"):
                with open(file_path, "r") as f:
                    content = f.read()
                    tokens = count_tokens(content)
                    self.context[f"File: {file_path}"] = content
                    print(f"Added {file_path} ({tokens} tokens)")
        else:
            print(f"File not found: {file_path}")

    async def cmd_run(self, cmd_parts):
        if len(cmd_parts) < 2:
            print("Please specify a command")
        else:
            command = " ".join(cmd_parts[1:])
            await self.run_command(command)

    async def cmd_multiline_mode(self, cmd_parts):
        self.multiline_mode = not self.multiline_mode
        self.session.multiline = self.multiline_mode
        state = "enabled" if self.multiline_mode else "disabled"
        print(f"Multiline mode {state}")

    async def cmd_paste(self, cmd_parts):
        try:
            output = subprocess.check_output(
                ["xclip", "-o", "-selection", "clipboard"]
            ).decode()
        except:
            try:
                output = subprocess.check_output(["wl-paste"]).decode()
            except:
                output = "Clipboard access failed"
                print(output)
                return
        print(output)
        tokens = count_tokens(output)
        if await self.confirm_action(
            f"Add clipboard content to context? ({tokens} tokens)"
        ):
            self.context["Pasted content"] = output

    async def cmd_scan(self, cmd_parts):
        print("scanning")

    async def cmd_test(self, cmd_parts):
        if len(cmd_parts) > 1:
            self.test_command = " ".join(cmd_parts[1:])
            print(f"Test command set: {self.test_command}")
        elif self.test_command:
            rc = await self.run_command(self.test_command)
            print(output)
            tokens = count_tokens(output)
            if await self.confirm_action(
                f"Add test output to context? ({tokens} tokens)"
            ):
                self.context[f"Command output: {self.test_command}"] = output
        else:
            print("No test command set")

    async def handle_command(self, user_input: str) -> bool:
        if user_input.startswith("/"):
            cmd_parts = user_input[1:].split()
            cmd = cmd_parts[0].lower()

            commands = {
                "exit": self.cmd_exit,
                "quit": self.cmd_exit,
                "help": self.cmd_help,
                "add": self.cmd_add,
                "run": self.cmd_run,
                "multiline-mode": self.cmd_multiline_mode,
                "paste": self.cmd_paste,
                "scan": self.cmd_scan,
                "test": self.cmd_test,
            }

            if cmd in commands:
                await commands[cmd](cmd_parts)
                return True
        return False

    async def run(self, callback):
        self.keep_running = True
        while self.keep_running:
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

        if await self.handle_command(user_input):
            return

        files = self.project.files()
        for token in user_input.split():
            for file in files:
                if file in token:
                    await self.file_add(file)

        for key, value in self.context.items():
            user_input += f"\n\n{key}:\n{value}"

        try:
            await callback(user_input)
        except Abort:
            pass

    async def diff_apply(self, diff):
        cli2.log.debug('diff_apply', diff=diff)

        from code2.diff import parse_unified_diff, reconstruct_unified_diff
        parsed = parse_unified_diff(diff)
        fixed_diff = reconstruct_unified_diff(parsed)
        if fixed_diff != diff:
            cli2.log.info('diff_fixed', diff=fixed_diff)

        if not await self.confirm_action(f"Apply changes to {parsed.new_filename}?"):
            return

        command = ['patch', '-u']
        if (
            parsed.old_filename.startswith('a/')
            and parsed.new_filename.startswith('b/')
        ):
            command.append('-p1')
        else:
            command.append('-p0')

        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate(
            input=fixed_diff.encode('utf8'),
        )

        stdout_str = stdout.decode('utf-8')
        stderr_str = stderr.decode('utf-8')
        if process.returncode != 0:
            hunk_problem = False
            for line in stdout_str.splitlines():
                if 'hunk FAILED -- saving rejects' in line:
                    hunk_problem = True
                    print(line)
                    with open(line.split()[-1], 'r') as f:
                        print(f.read())
                    if not await self.confirm_action('Apply hunk manually if you want, should we continue?'):
                        raise Abort()
            if hunk_problem:
                return

            with open('/tmp/patch', 'w') as f:
                f.write(fixed_diff)

            cli2.log.error(
                'patch',
                command=f'{" ".join(command)} < /tmp/patch',
                stdout=stdout_str,
                stderr=stderr_str,
                diff=diff,
            )
            raise subprocess.CalledProcessError(
                process.returncode,
                'patch',
                output=stdout_str,
                stderr=stderr_str,
            )

        return stdout_str, stderr_str
