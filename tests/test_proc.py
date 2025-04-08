import cli2
import os
import pytest


@pytest.mark.asyncio
async def test_proc_init_with_command_string():
    proc = cli2.Proc("echo hello")
    assert proc.args == ["echo", "hello"]
    assert proc.quiet is False
    assert proc.timeout is None
    assert proc.env == os.environ


@pytest.mark.asyncio
async def test_proc_init_with_command_and_args():
    proc = cli2.Proc("echo", "hello", "world")
    assert proc.args == ["echo", "hello", "world"]


@pytest.mark.asyncio
async def test_proc_init_with_quiet():
    proc = cli2.Proc("echo hello", quiet=True)
    assert proc.quiet is True


@pytest.mark.asyncio
async def test_proc_init_with_timeout():
    proc = cli2.Proc("echo hello", timeout=10)
    assert proc.timeout == 10


@pytest.mark.asyncio
async def test_proc_init_with_env():
    proc = cli2.Proc("echo hello", MY_VAR="test")
    assert proc.env["MY_VAR"] == "test"


@pytest.mark.asyncio
async def test_proc_clone():
    proc = cli2.Proc("echo hello", quiet=True, timeout=10, MY_VAR="test")
    cloned_proc = proc.clone()
    assert cloned_proc.args == proc.args
    assert cloned_proc.quiet == proc.quiet
    assert cloned_proc.timeout == proc.timeout
    assert cloned_proc.env == proc.env


@pytest.mark.asyncio
async def test_proc_cmd_property():
    proc = cli2.Proc("echo hello")
    assert proc.cmd == "echo hello"
    proc.cmd = "echo world"
    assert proc.args == ["echo", "world"]


@pytest.mark.asyncio
async def test_proc_start_and_wait():
    proc = cli2.Proc("echo hello")
    await proc.start()
    await proc.wait()
    assert proc.started is True
    assert proc.waited is True
    assert proc.rc == 0
    assert proc.out == "hello"


@pytest.mark.asyncio
async def test_proc_start_and_wait_with_timeout():
    proc = cli2.Proc("sleep 2", timeout=1)
    await proc.start()
    await proc.wait()
    assert proc.rc != 0  # Should be terminated due to timeout


@pytest.mark.asyncio
async def test_proc_output_properties():
    proc = cli2.Proc("echo hello")
    await proc.start()
    await proc.wait()
    assert proc.stdout == "hello"
    assert proc.stderr == ""
    assert proc.out == "hello"
    assert proc.stdout_ansi == "hello"
    assert proc.stderr_ansi == ""
    assert proc.out_ansi == "hello"


@pytest.mark.asyncio
async def test_proc_with_stderr():
    proc = cli2.Proc("bash", "-c", "echo error >&2 ")
    await proc.start()
    await proc.wait()
    assert proc.stdout == ""
    assert proc.stderr == "error"
    assert proc.out == "error"
    assert proc.stdout_ansi == ""
    assert proc.stderr_ansi == "error"
    assert proc.out_ansi == "error"


@pytest.mark.asyncio
async def test_proc_with_ansi_codes():
    proc = cli2.Proc("echo -e '\033[31mred\033[0m'")
    await proc.start()
    await proc.wait()
    assert proc.stdout == "red"
    assert proc.stdout_ansi == "\x1b[31mred\x1b[0m"


@pytest.mark.asyncio
async def test_proc_quiet_mode():
    proc = cli2.Proc("echo hello", quiet=True)
    await proc.start()
    await proc.wait()
    assert proc.out == "hello"


def test_proc_start_sync_and_wait_sync():
    proc = cli2.Proc("echo hello").wait_sync()
    assert proc.started is True
    assert proc.waited is True
    assert proc.rc == 0
    assert proc.out == "hello"


def test_proc_start_sync_and_wait_sync_with_timeout():
    proc = cli2.Proc("sleep 2", timeout=1).wait_sync()
    assert proc.rc != 0  # Should be terminated due to timeout


def test_proc_start_sync_and_wait_sync_with_stderr():
    proc = cli2.Proc("bash", "-c", "echo error >&2").wait_sync()
    assert proc.stdout == ""
    assert proc.stderr == "error"
    assert proc.out == "error"
    assert proc.stdout_ansi == ""
    assert proc.stderr_ansi == "error"
    assert proc.out_ansi == "error"


def test_proc_start_sync_and_wait_sync_with_ansi_codes():
    proc = cli2.Proc("echo -e '\033[31mred\033[0m'").wait_sync()
    assert proc.stdout == "red"
    assert proc.stdout_ansi == "\x1b[31mred\x1b[0m"


def test_proc_start_sync_and_wait_sync_quiet_mode():
    proc = cli2.Proc("echo hello", quiet=True).wait_sync()
    assert proc.out == "hello"
