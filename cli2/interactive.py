""" Interactive user inputs """
import os
import shlex
import subprocess
import tempfile

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

    :param content: Initial content if any
    :return: The edited content after $EDITOR exit
    """
    tmp = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".txt")
    with tmp as f:
        f.write(content)
        f.flush()
        filepath = f.name

    editor = os.getenv('EDITOR', 'vim')

    try:
        command = f"{editor} {shlex.quote(filepath)}"
        subprocess.run(shlex.split(command), check=True)

        with open(filepath, 'r') as f:
            content = f.read()
        return content
    except subprocess.CalledProcessError as e:
        log.error(f"Error running Vim: {e}")
        return None
    except FileNotFoundError:
        log.warn(f"Temporary file gone?? {filepath}")
        return None
    finally:
        try:
            os.remove(filepath)
        except OSError as e:
            log.warn(f"Error deleting temporary file {filepath}: {e}")
