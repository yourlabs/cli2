import asyncio
import inspect
import sys

from .argument import Argument


class Command(dict):
    def __init__(self, target, name=None, doc=None):
        self.target = target
        self.name = name or getattr(target, '__name__', type(target).__name__)
        self.doc = doc or inspect.getdoc(target)
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
            output.append(self.doc + '\n')

        return '\n'.join(output)

    def parse(self, *argv):
        self.bound = self.sig.bind_partial()
        extra = []
        for current in argv:
            taken = False
            for arg in self.values():
                if not arg.accepts:
                    continue

                if arg.iskw:
                    # we have reached keyword argument sequence
                    # see if another, further arg matches per alias and takes
                    reached = False
                    for _arg in self.values():
                        if taken:
                            break
                        if _arg == arg:
                            reached = True
                            continue
                        if not reached:
                            continue
                        if _arg.aliasmatch(current):
                            taken = _arg.take(current)

                if taken:
                    break

                taken = arg.take(current)
                if taken:
                    break

            if not taken:
                extra.append(current)

        if extra:
            return 'No parameters for these arguments: ' + ', '.join(extra)

    def __call__(self, argv=None):
        error = self.parse(*(argv if argv is not None else sys.argv[1:]))
        if error:
            return self.help(error)

        try:
            result = self.target(*self.bound.args, **self.bound.kwargs)
        except TypeError as exc:
            rep = getattr(self.target, '__name__')
            error = str(exc)
            if error.startswith(rep):
                return self.help(error.replace(rep, self.name))
            raise

        if inspect.iscoroutine(result):
            result = asyncio.run(result)
        return result
