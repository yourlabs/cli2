"""
Demonstration of a completely dynamic command line !
"""
import cli2
import inspect
from .node import Node


class ConsoleScript(cli2.Group):
    """
    cli2 makes your python callbacks work on CLI too !

    Show doc and callables for module cli2.test_node:

        cli2 cli2.test_node
        cli2 help cli2.test_node  # alternate

    Call cli2.test_node.example_function with args=['x'] and kwargs=dict(y='z')

        cli2 cli2.test_node.example_function x y=z
    """
    name = 'cli2'
    names = []

    def __call__(self, *argv):
        # Find if there's anything we should lazy load
        dotted = None
        if len(argv) > 1 and argv[0] == 'help':
            dotted = argv[1]
        elif argv:
            dotted = argv[0]

        if dotted:
            # Lazy load argument as command or group
            node = Node.factory(dotted)
            if callable(node.target):
                self.add(node.target, name=dotted)
            elif node.callables:
                self.group(
                    dotted,
                    doc=node.doc,
                    grpclass=type(self)
                ).load_module(dotted)

        self['help'].doc = 'Get help for a dotted path.'
        return super().__call__(*argv)

    def load_module(self, obj, parent=None, public=True):
        """Load a Python object callables into sub-commands."""
        if isinstance(obj, str):
            obj = Node.factory(obj).target

        objpackage = getattr(obj, '__package__', None)

        for name in dir(obj):
            if name == '__call__':
                target = obj
                name = type(obj).__name__
            elif name.startswith('__' if not public else '_'):
                continue
            else:
                target = getattr(obj, name)

            if name in self.names:
                continue
            self.names.append(name)

            targetpackage = getattr(target, '__package__', None)
            if targetpackage and objpackage:
                # prevent recursively loading from other packages
                # and above obj level
                if not targetpackage.startswith(objpackage):
                    continue

            if target == parent:
                # detect and prevent recursive imports
                continue

            if callable(target):
                try:
                    inspect.signature(target)
                except ValueError:
                    pass
                else:
                    self.add(target, name=name)
                continue

            node = Node(name, target)
            if node.callables:
                self.group(
                    name,
                    grpclass=type(self)
                ).load_module(target, parent=obj)
        return self


main = ConsoleScript()
