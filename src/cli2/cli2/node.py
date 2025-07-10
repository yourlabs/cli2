import inspect
import importlib
import types


class Node:
    """
    A Python node, used to browse python module programatically for callables.
    """
    def __init__(self, name, target, module=None):
        self.name = name
        self.target = target

        if module:
            self.module = module
        elif isinstance(target, types.ModuleType):
            self.module = target
        elif hasattr(target, '__module__'):
            self.module = target.__module__
        else:
            self.module = None

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.target == other.target
        return self.target == other

    def __str__(self):
        return self.name

    def __repr__(self):
        return f'Node({self.name})'

    @property
    def doc(self):
        return inspect.getdoc(self.target)

    @property
    def type(self):
        if isinstance(self.target, types.ModuleType):
            return 'module'
        if isinstance(self.target, types.FunctionType):
            return 'function'

    @property
    def callables(self):
        """Return the list of callables in this Node."""
        results = []
        builtins = (types.BuiltinFunctionType, types.BuiltinMethodType)
        for name, member in inspect.getmembers(self.target):
            if not callable(member):
                continue
            if name.startswith('__') or isinstance(member, builtins):
                continue  # skip builtins
            results.append(Node(name, member))
        return results

    @classmethod
    def factory(cls, name):
        """
        Return a Node based on a string dotted python path.

        Examples::

            Node.factory('your.module')
            Node.factory('your.module.your_object')
            Node.factory('your.module.your_object.some_attribute')
        """
        module = None
        parts = name.split('.')
        for i, part in reversed(list(enumerate(parts))):
            modname = '.'.join(parts[:i + 1])

            if not modname:
                break

            try:
                module = importlib.import_module(modname)
            except ImportError:
                continue
            else:
                break

        if module:
            ret = module
            for part in parts[i + 1:]:
                if isinstance(ret, dict) and part in ret:
                    ret = ret.get(part)
                elif isinstance(ret, list) and part.isnumeric():
                    ret = ret[int(part)]
                else:
                    ret = getattr(ret, part, None)
        else:
            ret = None

        return cls(name, ret, module)
