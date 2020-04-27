import asyncio
import inspect

from .argument import Argument
from .colors import colors
from .entry_point import EntryPoint


class Command(EntryPoint, dict):
    def __init__(self, target, name=None, doc=None, color=None):
        self.target = target
        self.name = name or getattr(target, '__name__', type(target).__name__)
        self.doc = doc or inspect.getdoc(target)
        self.color = color or colors.orange

        overrides = getattr(target, 'cli2', {})
        for key, value in overrides.items():
            setattr(self, key, value)

        if self.color in colors.__dict__:
            self.color = getattr(colors, self.color)

        self.sig = inspect.signature(target)

        for name, param in self.sig.parameters.items():
            self[name] = Argument(self, param)
            overrides = getattr(self.target, 'cli2_' + name, {})
            for key, value in overrides.items():
                setattr(self[name], key, value)

    def help(self, error=None, short=False):
        output = []

        if error:
            output.append(error + '\n')

        if self.doc:
            if short:
                # get the first sentence
                sentence = ''
                for char in self.doc.replace('\n', ' '):
                    if char == '.':
                        break
                    sentence += char
                output.append(sentence)
            else:
                output.append(self.doc + '\n')

        return '\n'.join(output)

    def parse(self, *argv):
        self.bound = self.sig.bind_partial()
        extra = []
        for current in argv:

            taken = False
            for arg in self.values():
                taken = arg.take(current)
                if taken:
                    break

            if not taken:
                extra.append(current)

        if extra:
            return 'No parameters for these arguments: ' + ', '.join(extra)

    def __call__(self, *argv):
        self.exit_code = 0
        error = self.parse(*argv)
        if error:
            return self.help(error)

        try:
            result = self.target(*self.bound.args, **self.bound.kwargs)
        except TypeError as exc:
            self.exit_code = 1
            rep = getattr(self.target, '__name__')
            error = str(exc)
            if error.startswith(rep):
                return self.help(error.replace(rep, self.name))
            raise

        if inspect.iscoroutine(result):
            result = asyncio.run(result)
        return result
