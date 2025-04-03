import asyncio
import subprocess
from pathlib import Path

import pytest
from code2.diff import parse_unified_diff, reconstruct_unified_diff

@pytest.fixture
def diff_with_noop_hunk():
    # This diff has two hunks.
    # The first hunk is a no-op (removal and addition are identical) and should be discarded.
    # Only the second hunk, which removes the bottom_toolbar line, is kept.
    diff_text = (
        "--- a/code2/code2/shell.py\r\n"
        "+++ b/code2/code2/shell.py\r\n"
        "@@ -46,7 +46,6 @@\r\n"
        "             complete_in_thread=True,\r\n"
        "         )\r\n"
        "\r\n"
        "-        self.session = PromptSession(\r\n"
        "+        self.session = PromptSession(\r\n"
        "             lexer=PygmentsLexer(PythonLexer),\r\n"
        "             history=FileHistory(history_file),\r\n"
        "             message=\"code2> \",\r\n"
        "@@ -54,7 +53,6 @@\r\n"
        "             completer=CommandCompleter(),\r\n"
        "-            bottom_toolbar=\"[Ctrl+D] exit, [Ctrl+L] clear, [Ctrl+X Ctrl+E] vim\",\r\n"
        "             multiline=False,\r\n"
        "             complete_while_typing=True,\r\n"
        "             complete_in_thread=True,\r\n"
    )
    return diff_text

@pytest.fixture
def sample_diff_newfile():
    # Diff for a new file; header originally indicates "+1,11" but there are actually 12 lines.
    diff_text = (
        "--- /dev/null\r\n"
        "+++ hello_world_1743684790.py\r\n"
        "@@ -0,0 +1,11 @@\r\n"
        "+import sys\r\n"
        "+\r\n"
        "+def hello_world(message=None):\r\n"
        "+    if message is None:\r\n"
        "+        if len(sys.argv) > 1:\r\n"
        "+            message = sys.argv[1]\r\n"
        "+        else:\r\n"
        "+            message = \"Default Message\"\r\n"
        "+    print(f\"Hello, World!\\n{message}\")\r\n"
        "+\r\n"
        "+if __name__ == \"__main__\":\r\n"
        "+    hello_world()\r\n"
    )
    return diff_text

@pytest.fixture
def git_style_diff():
    # Git-style diff with "a/" and "b/" prefixes.
    diff_text = (
        "--- a/code2/code2/shell.py\r\n"
        "+++ b/code2/code2/shell.py\r\n"
        "@@ -1,3 +1,3 @@\r\n"
        " line1\r\n"
        "-line2\r\n"
        "+line2_fixed\r\n"
        " line3\r\n"
    )
    return diff_text

@pytest.fixture
def bare_path_diff():
    # Diff with bare file paths (no "a/" or "b/").
    diff_text = (
        "--- code2/code2/shell.py\r\n"
        "+++ code2/code2/shell.py\r\n"
        "@@ -50,6 +50,6 @@\r\n"
        "             complete_in_thread=True,\r\n"
        "         )\r\n"
        "\r\n"
        "-        self.session = PromptSession(\r\n"
        "+        self.session = PromptSession(\r\n"
        "             lexer=PygmentsLexer(PythonLexer),\r\n"
        "             history=FileHistory(history_file),\r\n"
        "             message=\"code2> \",\r\n"
        "@@ -58,5 +57,4 @@\r\n"
        "             completer=CommandCompleter(),\r\n"
        "-            bottom_toolbar=\"[Ctrl+D] exit, [Ctrl+L] clear, [Ctrl+X Ctrl+E] vim\",\r\n"
        "             multiline=False,\r\n"
        "             complete_while_typing=True,\r\n"
        "             complete_in_thread=True,\r\n"
        "@@ -103,2 +101,10 @@\r\n"
        "             output.append(decoded_line)\r\n"
        "\r\n"
        "-        return process.returncode\r\n"
        "+        await process.wait()\r\n"
        "+\r\n"
        "+        output = \"\\n\".join(output)\r\n"
        "+        print(output)\r\n"
        "+        tokens = count_tokens(output)\r\n"
        "+        if await self.confirm_action(f\"Add output to context? ({tokens} tokens)\"):\r\n"
        "+            self.context[f\"Command output: {command}\"] = output\r\n"
        "+\r\n"
        "+        return process.returncode\r\n"
        "@@ -263,4 +268,11 @@\r\n"
        "             return True\r\n"
        "         return False\r\n"
        "\r\n"
        "+    async def reset_prompt(self):\r\n"
        "+        self.session.message = \"code2> \"\r\n"
        "+        self.session.bottom_toolbar = None\r\n"
        "+        self.session.completer = CommandCompleter()\r\n"
        "+        self.session.multiline = self.multiline_mode\r\n"
        "+\r\n"
        "     async def run(self, callback):\r\n"
        "         self.keep_running = True\r\n"
        "@@ -277,4 +289,5 @@\r\n"
        "             except Exception as e:\r\n"
        "                 cli2.log.exception()\r\n"
        "\r\n"
        "+            await self.reset_prompt()\r\n"
        "\r\n"
        "     async def run_once(self, callback):\r\n"
        "         user_input = await self.session.prompt_async()\r\n"
    )
    return diff_text

def test_noop_hunk_filtering(diff_with_noop_hunk):
    parsed = parse_unified_diff(diff_with_noop_hunk)
    # The first hunk is a no-op and should be discarded.
    # Only one hunk should remain (the one that removes bottom_toolbar).
    assert len(parsed.hunks) == 1
    # For non-new-file diffs, we preserve the original header counts.
    reconstructed = reconstruct_unified_diff(parsed)
    # The reconstructed diff should contain the original header for the second hunk.
    assert "@@ -54,7 +53,6 @@" in reconstructed
    # It should not include any line with "self.session = PromptSession(".
    assert "PromptSession(" not in reconstructed

def test_parser_and_reconstruction(sample_diff_newfile):
    parsed = parse_unified_diff(sample_diff_newfile)
    assert parsed.old_filename == "/dev/null"
    assert parsed.new_filename == "hello_world_1743684790.py"
    # For a new file diff, the hunk header should be recalculated.
    hunk = parsed.hunks[0]
    assert hunk.old_count == 0
    assert hunk.new_count == 12
    reconstructed = reconstruct_unified_diff(parsed)
    assert "\r\n" not in reconstructed
    assert "@@ -0,0 +1,12 @@" in reconstructed

def test_git_style_strip_count(git_style_diff):
    parsed = parse_unified_diff(git_style_diff)
    # With git-style prefixes, the suggested strip count should be 1.
    assert parsed.strip_count == 1

def test_bare_path_strip_count(bare_path_diff):
    parsed = parse_unified_diff(bare_path_diff)
    # With bare paths, no stripping is suggested.
    assert parsed.strip_count == 0

def test_patch_application(tmp_path, sample_diff_newfile):
    target_file = tmp_path / "hello_world_1743684790.py"
    # Write an empty file to simulate /dev/null for a new file.
    target_file.write_text("")
    parsed = parse_unified_diff(sample_diff_newfile)
    fixed_diff = reconstruct_unified_diff(parsed)
    diff_file = tmp_path / "patch.diff"
    diff_file.write_text(fixed_diff)
    process = subprocess.run(
        ["patch", str(target_file), str(diff_file)],
        capture_output=True,
        text=True,
        cwd=tmp_path
    )
    assert process.returncode == 0, f"Patch failed: {process.stderr}"
    expected = (
        "import sys\n"
        "\n"
        "def hello_world(message=None):\n"
        "    if message is None:\n"
        "        if len(sys.argv) > 1:\n"
        "            message = sys.argv[1]\n"
        "        else:\n"
        "            message = \"Default Message\"\n"
        "    print(f\"Hello, World!\\n{message}\")\n"
        "\n"
        "if __name__ == \"__main__\":\n"
        "    hello_world()\n"
    )
    new_content = target_file.read_text()
    assert new_content == expected, f"Patched content did not match expected. Got: {new_content}"

@pytest.mark.asyncio
async def test_patch_application_async(tmp_path, sample_diff_newfile):
    target_file = tmp_path / "hello_world_1743684790.py"
    target_file.write_text("")
    parsed = parse_unified_diff(sample_diff_newfile)
    fixed_diff = reconstruct_unified_diff(parsed)
    diff_file = tmp_path / "patch.diff"
    diff_file.write_text(fixed_diff)
    process = await asyncio.create_subprocess_exec(
        'patch',
        '-u',
        str(target_file),
        str(diff_file),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE,
        cwd=str(tmp_path)
    )
    stdout, stderr = await process.communicate(input=fixed_diff.encode('utf8'))
    assert process.returncode == 0, f"Patch failed: {stderr.decode()}"
    expected = (
        "import sys\n"
        "\n"
        "def hello_world(message=None):\n"
        "    if message is None:\n"
        "        if len(sys.argv) > 1:\n"
        "            message = sys.argv[1]\n"
        "        else:\n"
        "            message = \"Default Message\"\n"
        "    print(f\"Hello, World!\\n{message}\")\n"
        "\n"
        "if __name__ == \"__main__\":\n"
        "    hello_world()\n"
    )
    new_content = target_file.read_text()
    assert new_content == expected, f"Patched content did not match expected. Got: {new_content}"

