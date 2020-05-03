"""
Demonstration of a completely dynamic command line !
"""
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
    name = 'cli2'

    def __call__(self, *argv):
        # Find if there's anything we should lazy load
        dotted = None
        if len(argv) > 1 and argv[0] == 'help':
            dotted = argv[1]
        elif argv:
            dotted = argv[0]

        if dotted:
            # Lazy load argument as command or group
            node = cli2.Node.factory(dotted)
            if callable(node.target):
                self.add(node.target, name=dotted)
            elif node.callables:
                self.group(dotted, doc=node.doc).load(dotted)

        self['help'].doc = 'Get help for a dotted path.'
        return super().__call__(*argv)


main = ConsoleScript()
