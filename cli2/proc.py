"""
Asyncio subprocess wrapper featuring:

- Capture + live logging of stdout/stderr
- ANSI escape code cleaning for captured output: print colored output for
  humans, have clean output in a variable for processing, log, cache... and
  sending to LLMs!
- Separate start/wait methods for process control

Example usage:

.. code-block:: python

    # pass shell command in a string for convenience
    proc = cli2.Proc('foo bar')

    # or as list, better when building commands
    proc = await cli2.Proc('foo', 'bar')

    # wait in async loop
    await proc.wait()

.. note:: There are also start functions, sync and async, in case you want to
          start the proc and wait later.
"""
import asyncio
import os
import shlex
import re

from .log import log

ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class Proc:
    """
    Asynchronous subprocess manager with advanced IO handling.

    .. py:attribute:: args

        Full command arguments list used to launch the process

    .. py:attribute:: env

        Dict of environment variables

    .. py:attribute:: cwd

        Working directory path to run the command in

    .. py:attribute:: rc

        Return Code: process exit code (available after process completes)

    .. py:attribute:: out

        Combined cleaned output with ANSI escape codes removed.

    .. py:attribute:: out_ansi

        Combined stdout/stderr output with ANSI codes preserved.

    .. py:attribute:: stdout

        Cleaned stdout output with ANSI escape codes removed.

    .. py:attribute:: stderr

        Cleaned stdout output with ANSI escape codes removed.

    .. py:attribute:: stdout_ansi

        Stdout output with ANSI escape codes preserved.

    .. py:attribute:: stderr_ansi

        Stderr output with ANSI escape codes preserved.
    """
    def __init__(self, cmd, *args, quiet=False, inherit=True, timeout=None,
                 cwd=None, **env):
        """
        :param cmd: Command string (will shlex split) or initial argument
        :param args: Additional command arguments
        :param quiet: Suppress live output printing (default: False)
        :param inherit: Inherit parent environment variables (default: True)
        :param timeout: Maximum execution time in seconds (default: None)
        :param env: Additional environment variables to set
        :type env: Environment variables.
        """
        if args:
            self.args = [cmd] + list(args)
        else:
            self.args = shlex.split(cmd)

        self.cwd = cwd or os.getcwd()
        self.quiet = quiet

        self.env = dict()
        if inherit:
            self.env = os.environ.copy()
        self.env.update(env)

        self.out_raw = bytearray()
        self.err_raw = bytearray()
        self.raw = bytearray()

        self.started = False
        self.waited = False
        self.timeout = timeout
        self.rc = None
        self.proc = None

    def clone(self):
        """
        Create a new unstarted Proc instance with identical configuration.

        :return: New Proc instance ready for execution
        """
        return type(self)(
            *self.args, quiet=self.quiet, inherit=True, timeout=self.timeout,
            **self.env
        )

    @property
    def cmd(self):
        """
        Get/set the command as a shell-joinable string.

        :getter: Returns shell-escaped command string
        :setter: Parses and updates internal args list
        :type: str
        """
        return shlex.join(self.args)

    @cmd.setter
    def cmd(self, value):
        self.args = shlex.split(value)

    async def start(self):
        """
        Launch the subprocess asynchronously.

        :return: Self reference for method chaining
        :raises RuntimeError: If process is already started
        """
        if self.started:
            raise RuntimeError("Process already started")

        if not self.quiet:
            log.debug('cmd', cmd=self.cmd)

        self.proc = await asyncio.create_subprocess_exec(
            *[str(arg) for arg in self.args],
            cwd=str(self.cwd),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={str(k): str(v) for k, v in self.env.items()},
        )
        self.started = True

        self.stdout_task = asyncio.create_task(
            self._handle_output(self.proc.stdout, 1)
        )
        self.stderr_task = asyncio.create_task(
            self._handle_output(self.proc.stderr, 2)
        )
        return self

    async def wait(self):
        """
        Wait for process completion with timeout handling.

        Terminates process if timeout occurs. Gathers all output streams.

        :return: Self reference for method chaining
        """
        if not self.started:
            await self.start()

        try:
            if self.timeout:
                await asyncio.wait_for(self.proc.wait(), timeout=self.timeout)
            else:
                await self.proc.wait()
        except asyncio.TimeoutError:
            print(f"Process timed out after {self.timeout}s")
            self.proc.terminate()
            await self.proc.wait()

        await asyncio.gather(self.stdout_task, self.stderr_task)
        self.rc = self.proc.returncode
        self.waited = True
        return self

    async def _handle_output(self, stream, fd):
        """
        Internal method for stream handling.

        :param stream: Output stream to monitor
        :type stream: asyncio.StreamReader
        :param fd: Stream identifier (1=stdout, 2=stderr)
        :type fd: int
        """
        while True:
            line = await stream.readline()
            if not line:  # EOF
                break

            decoded_line = line.decode().rstrip()
            if fd == 1:  # stdout
                self.out_raw.extend(line)
            elif fd == 2:  # stderr
                self.err_raw.extend(line)
            self.raw.extend(line)

            if not self.quiet:
                print(decoded_line)

    @property
    def stdout_ansi(self):
        return self.out_raw.decode().rstrip()

    @property
    def stderr_ansi(self):
        return self.err_raw.decode().rstrip()

    @property
    def out_ansi(self):
        return self.raw.decode().rstrip()

    @property
    def stdout(self):
        return ansi_escape.sub('', self.stdout_ansi)

    @property
    def stderr(self):
        return ansi_escape.sub('', self.stderr_ansi)

    @property
    def out(self):
        return ansi_escape.sub('', self.out_ansi)
