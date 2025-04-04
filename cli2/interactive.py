""" Interactive user inputs """


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
