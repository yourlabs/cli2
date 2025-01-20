import logging
import os
import sys

from .colors import colors
from . import display


class EntryPoint:
    def __init__(self, *args, outfile=None, log=True, **kwargs):
        self.outfile = outfile or sys.stdout
        self.exit_code = 0
        self.log = log
        super().__init__(*args, **kwargs)

    def entry_point(self, *args):
        args = args or sys.argv
        self.name = os.path.basename(args[0])

        if self.log:
            logging.basicConfig(
                stream=sys.stdout,
                level=getattr(
                    logging,
                    os.environ.get('LOG', 'info').upper(),
                ),
            )

        result = self(*args[1:])
        if result is not None:
            try:
                display.print(result)
            except:  # noqa
                print(result)
        sys.exit(self.exit_code)

    def print(self, *args, sep=' ', end='\n', file=None, color=None):
        if args and args[0].lower() in colors.__dict__ and not color:
            color = args[0]
            args = args[1:]
            if color.lower() != color:
                color = color.lower() + 'bold'
            color = getattr(colors, color)

        msg = sep.join(map(str, args))

        if color:
            msg = color + msg + colors.reset

        print(msg, end=end, file=file or self.outfile, flush=True)

    @property
    def path(self):
        """
        Return the CLI sub-command path.
        """
        current = self
        chain = []
        while current is not None:
            chain.insert(0, current.name)
            current = current.parent
        return " ".join(chain)

    @property
    def doc_short(self):
        """
        Return the first sentence of the documentation.
        """
        tokens = []
        for line in self.doc.split('\n'):
            if not line.strip():
                break
            tokens.append(line)
        if tokens and tokens[-1].endswith('.'):
            tokens[-1] = tokens[-1][:-1]
        return ' '.join(tokens) if tokens else ''
