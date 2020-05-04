import os
import sys

from .colors import colors


class EntryPoint:
    def __init__(self, *args, outfile=None, **kwargs):
        self.outfile = outfile or sys.stdout
        self.exit_code = 0
        super().__init__(*args, **kwargs)

    def entry_point(self):
        if not self.name:
            self.name = os.path.basename(sys.argv[0])
        result = self(*sys.argv[1:])
        if result is not None:
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
