import asyncio
import inspect

from .argument import Argument
from .colors import colors
from .entry_point import EntryPoint


class Command(EntryPoint, dict):
    def __new__(cls, target, *args, **kwargs):
        overrides = getattr(target, 'cli2', {})
        cls = overrides.get('cls', cls)
        return super().__new__(cls, *args, **kwargs)

    def __init__(self, target, name=None, color=None, doc=None):
        self.target = target

        overrides = getattr(target, 'cli2', {})
        for key, value in overrides.items():
            setattr(self, key, value)

        if name:
            self.name = name
        elif 'name' not in overrides:
            self.name = getattr(target, '__name__', type(target).__name__)

        if doc:
            self.doc = doc
        elif 'doc' not in overrides:
            self.doc = inspect.getdoc(target)

        if color:
            self.color = color
        elif 'color' not in overrides:
            self.color = colors.orange

        if self.color in colors.__dict__:
            self.color = getattr(colors, self.color)

        self.sig = inspect.signature(target)
        self.setargs()

    def setargs(self):
        for name, param in self.sig.parameters.items():
            overrides = getattr(self.target, 'cli2_' + name, {})
            cls = overrides.get('cls', Argument)
            self[name] = cls(self, param)
            for key, value in overrides.items():
                setattr(self[name], key, value)

    @classmethod
    def cmd(cls, *args, **kwargs):
        def override(target):
            overrides = getattr(target, 'cli2', {})
            overrides.update(kwargs)
            overrides['cls'] = cls
            target.cli2 = overrides

        if len(args) == 1 and not kwargs:
            # simple @YourCommand.cmd syntax
            target = args[0]
            override(target)
            return target
        elif not args:
            def wrap(cb):
                override(cb)
                return cb
            return wrap
        else:
            raise Exception('Only kwargs are supported by Group.cmd')

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
        self.setargs()
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

    def call(self):
        return self.target(*self.bound.args, **self.bound.kwargs)

    def __call__(self, *argv):
        self.exit_code = 0
        error = self.parse(*argv)
        if error:
            return self.help(error)

        try:
            result = self.call()
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
