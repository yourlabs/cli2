"""
Demonstration of a completely dynamic command line !
"""
import inspect

import cli2


class ConsoleScript(cli2.Group):
    """
    cli2 makes your python callbacks work on CLI too !

    Show doc and callables for module cli2.test_node:

        cli2 cli2.test_node
        cli2 help cli2.test_node  # alternate

    Call cli2.test_node.example_function with args=['x'] and kwargs=dict(y='z')

        cli2 cli2.test_node.example_function x y=z
    """

    def load(self, dotted_path):
        node = cli2.Node.factory(dotted_path)
        if callable(node.target):
            self[dotted_path] = cli2.Command(node.target)
        else:
            self[dotted_path] = cli2.Group(
                dotted_path,
                doc=inspect.getdoc(node.target),
            )
            self[dotted_path].load(node.target)

    def __call__(self, *argv):
        def arghelp(dotted_path):
            """
            Get help and callables for a dotted_path.
            """
            self.load(dotted_path)
            return self[dotted_path].help()

        self['help'] = cli2.Command(arghelp, color=cli2.c.green)

        if not argv or argv == ('help',):
            return self.help()

        if argv[0] == 'help':
            self.load(argv[1])
        else:
            self.load(argv[0])

        return super().__call__(*argv)


main = ConsoleScript()
