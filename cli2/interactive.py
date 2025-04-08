""" Interactive user inputs """
import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from .log import log


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


def editor(content=None):
    """
    Open $EDITOR with content, return the result.

    Like git rebase -i does!

    - If a file path is given, edit in place.
    - Otherwise, write to a temporary file.
    - Anyway: return the written contents.

    :param content: Initial content if any, or a file path
    :return: The edited content after $EDITOR exit
    """
    editor = os.getenv('EDITOR', 'vim')

    if Path(content).exists():
        # open directly on target path
        filepath = content
        tmp = None
    else:
        tmp = tempfile.NamedTemporaryFile(
            mode='w+',
            delete=False,
            suffix=".txt",
        )
        with tmp as f:
            f.write(content)
            f.flush()
            filepath = f.name

    command = f"{editor} {shlex.quote(str(filepath))}"

    try:
        subprocess.run(shlex.split(command), check=True)
    except subprocess.CalledProcessError as e:
        log.error(f"Error running Vim: {e}")
        return None
    except FileNotFoundError:
        log.warn(f"Temporary file gone?? {filepath}")
        return None
    else:
        with open(filepath, 'r') as f:
            content = f.read()
        return content
    finally:
        if tmp:
            try:
                os.remove(filepath)
            except OSError as e:
                log.warn(f"Error deleting temporary file {filepath}: {e}")
