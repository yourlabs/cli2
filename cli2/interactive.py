""" Interactive user inputs """
import cli2
import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from .log import log


def confirm(question, default=None):
    return choice(question, default=default) == 'y'


def choice(question, choices=None, default=None):
    """
    Ask user to make a choice.

    .. code-block::

        accepted = cli2.choice('Accept terms?') == 'y'

    :param question: String question to ask
    :param choices: List of acceptable choices, y/n by default
    :param default: Default value for when the user does not add a value.
    """
    choices = [c.lower() for c in choices or ['y', 'n']]

    if default:
        choices_display = [
            c.upper() if c == default.lower() else c
            for c in choices
        ]
    else:
        choices_display = choices

    question = question + f' ({"/".join(choices_display)})'

    tries = 30
    while tries:
        answer = input(question)
        if not answer and default:
            return default

        if answer.lower() in choices:
            return answer.lower()

        tries -= 1


def editor(content=None, path=None):
    """
    Open $EDITOR with content, return the result.

    Like git rebase -i does!

    - If a file path is given, edit in place.
    - Otherwise, write to a temporary file.
    - Anyway: return the written contents.

    :param content: Initial content if any
    :param path: Path to edit or write content into
    :return: The edited content after $EDITOR exit
    """
    editor = os.getenv('EDITOR', 'vim')

    tmp_file = None
    if path and path.exists():
        edit_path = path
    else:
        suffix = 'txt' if not path else path.name.split('.')[-1]
        tmp = tempfile.NamedTemporaryFile(
            mode='w+',
            delete=False,
            suffix=f'.{suffix}',
        )
        edit_path = tmp.name
        if content:
            with tmp as f:
                cli2.log.debug('writing', path=f.name)
                f.write(str(content))
                f.flush()
                tmp_file = Path(f.name)

    cli2.log.debug('editing', path=edit_path)
    command = f"{editor} {shlex.quote(str(edit_path))}"

    try:
        subprocess.run(shlex.split(command), check=True)
    except subprocess.CalledProcessError as e:
        log.error(f"Error running Vim: {e}")
        return None
    except FileNotFoundError:
        log.warn(f"Temporary file gone?? {path}")
        return None
    else:
        with open(edit_path, 'r') as f:
            cli2.log.debug('reading', path=edit_path)
            content = f.read()
        if path and not path.exists():
            path.parent.mkdir(exist_ok=True, parents=True)
            with path.open('w') as f:
                cli2.log.debug('writing', path=path)
                f.write(content)
        return content
    finally:
        if tmp_file:
            try:
                os.remove(tmp_file)
            except OSError as e:
                log.warn(f"Error deleting temporary file {tmp_file}: {e}")
