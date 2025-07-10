"""
Color themes.

The theme is available in the `cli2.t` namespace.

.. envar:: CLI2_THEME

    The default is "monokai", but "standard" and "flashy" are also available.
    Standard theme uses basic colors, and lets you override them with
    environment variables: CLI2_RED, CLI2_GREEN, and so on.

Example:

.. code-block:: python

    import cli2

    print(f'{cli2.theme.green}OK{cli2.theme.reset}')

    # with a mode, such as bold, dim, italic, underline and strike:
    print(f'{cli2.theme.green.bold}OK{cli2.theme.reset}')

    # all is also callable appending the reset automatically
    print(cli2.theme.green('OK'))
    print(cli2.theme.green.bold('OK'))

We also have shortcuts, ``cli2.theme`` is ``cli2.t``, each color can be
referred to by first letter in lowercase, except for black and gray which are
refered to by their first letter in uppercase. Modes can be referred to by
first letter in lowercase too, and reset is rs:

.. code-block:: python

    # shortcuts
    print(f'{cli2.t.g.b}OK{cli2.t.rs}')

    # shorter with callable
    print(cli2.t.g.b('OK'))

Run ``cli2-theme`` for the list of colors by theme.
"""
import re
import os


themes = dict(
    standard=dict(
        black=int(os.getenv('CLI2_BLACK', 0)),
        red=int(os.getenv('CLI2_RED', 1)),
        green=int(os.getenv('CLI2_GREEN', 2)),
        yellow=int(os.getenv('CLI2_YELLOW', 3)),
        orange=int(os.getenv('CLI2_ORANGE', 208)),
        blue=int(os.getenv('CLI2_BLUE', 4)),
        mauve=int(os.getenv('CLI2_MAUVE', 5)),
        pink=int(os.getenv('CLI2_PINK', 164)),
        cyan=int(os.getenv('CLI2_CYAN', 6)),
        gray=int(os.getenv('CLI2_GRAY', 7)),
    ),
    flashy=dict(
        black=0,
        red=196,
        green=46,
        yellow=227,
        blue=27,
        mauve=129,
        pink=201,
        orange=202,
        cyan=51,
        gray=253,
    ),
    monokai=dict(
        black=0,
        red=124,
        green=150,
        yellow=179,
        blue=67,
        mauve=140,
        pink=132,
        orange=202,
        cyan=80,
        gray=246,
    ),
)


class Renderer:
    def __call__(self, *content):
        return f'{self}{" ".join([str(c) for c in content])}{t.rs}'


class Mode(Renderer):
    def __init__(self, name, code):
        self.name = name
        self.code = code
        self.alias = name[0]

    def __str__(self):
        return f'\u001b[{self.code}m'


class ColorMode(Renderer):
    def __init__(self, color, mode):
        self.color = color
        self.mode = mode

    def __str__(self):
        return f'\u001b[{self.mode.code};38;5;{self.color.code}m'


modes = {
    name: Mode(name, code)
    for name, code in dict(
        bold=1,
        dim=2,
        italic=3,
        underline=4,
        strike=9,
    ).items()
}


class Color(Renderer):
    def __init__(self, code, name=None, alias=None):
        self.name = name
        self.alias = alias
        self.code = code

        for mode, code in modes.items():
            color_mode = ColorMode(self, code)
            setattr(self, mode, color_mode)
            setattr(self, mode[0], color_mode)

    def __str__(self):
        return f'\u001b[38;5;{self.code}m'


class Theme:
    def __init__(self, colors=None):
        self.colors = colors or themes[os.getenv('CLI2_THEME', 'monokai')]

        for name, mode in modes.items():
            setattr(self, mode.name, mode)

        for name, value in self.colors.items():
            if name in ('black', 'gray'):
                alias = name[0].upper()
            else:
                alias = name[0]

            color = Color(value, name, alias)
            setattr(self, name, color)
            setattr(self, alias, color)

        for name in ('reset', 'rs'):
            setattr(self, name, '\u001b[0m')

    @staticmethod
    def len(string):
        """
        Counts the number of alphabetic characters in a string,
        ignoring ANSI escape codes.

        :param string: Input string
        :return: Integer count of actual printable chars
        """
        # Regular expression to match ANSI escape codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

        # Remove ANSI escape codes from the string
        cleaned_text = ansi_escape.sub('', string)

        # Count the alphabetic characters in the cleaned string
        letter_count = 0
        for char in cleaned_text:
            if 'a' <= char <= 'z' or 'A' <= char <= 'Z':
                letter_count += 1

        return letter_count


t = theme = Theme()


def demo():
    """
    Print all colors and modes from the theme.
    """
    for name, theme in themes.items():
        theme = Theme(themes[name])
        print(f'\n\nTheme: {theme.bold(name)}')
        _demo(theme)

    print()
    print(theme.bold('MODES:'))
    for name in modes:
        mode = getattr(theme, name)
        print(f'{mode}t.{name}{t.rs}')


def _demo(theme):
    def color_data(alias, color):
        data = [
            (color, alias),
        ]

        for mode in modes:
            data.append(
                (getattr(color, mode[0]), f'{alias}.{mode[0]}'),
            )

        return data

    from .table import Table
    table = Table()
    for name in t.colors:
        color = getattr(theme, name)

        table.append(color_data(color.alias, color))
    table.print()


def main():
    from .cli import Command
    return Command(demo).entry_point()
