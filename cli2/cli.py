"""
cli2 makes your python callbacks work on CLI too !
"""

import inspect

import cli2


def run(dotted_path):
    node = Node.factory(dotted_path)
    if not node.target:
        return 'Not found ' + str(node)
    print(inspect.getdoc(node.target))
    breakpoint()
    for sub in node.callables:
        print(sub)


console_script = cli2.Command(run)
