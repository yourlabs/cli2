.. image:: https://yourlabs.io/oss/cli2/badges/master/pipeline.svg
   :target: https://yourlabs.io/oss/cli2/pipelines
.. image:: https://codecov.io/gh/yourlabs/cli2/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/yourlabs/cli2
.. image:: https://img.shields.io/pypi/v/cli2.svg
   :target: https://pypi.python.org/pypi/cli2

cli2: Dynamic CLI for Python 3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Expose Python functions or objects with a minimalist argument typing style, or
building your own command try during runtime.

`Documentation available on RTFD
<https://cli2.rtfd.io>`_.

Demo
====

cli2 is a little library to build CLIs, which documentation is `available on
RTFD <https://cli2.readthedocs.io/en/latest/>`_, but it comes with its own demo
command that may as well be useful.

Initially, cli2 was supposed to just bring Python callables on the CLI without
even a single line of code::

    cli2 path.to.your.callable arg1 kwarg1=value

This command was implemented again in this 10th rewrite of the CLI engine
extracted from Playlabs, however this implementation features something pretty
funny: cli2 is a Group subclass which overrides the default Group
implementation based on the first argument passed on the command line.

Basically, when you call ``cli2 path.to.module``, it will load a Group of name
``path.to.module`` which whill load one Command per callable in
``path.to.module``.

When you call ``cli2 path.to.function`` it will execute the function.

As a result, these two commands are strictly equivalent::

    cli2 cli2.test_node example_function foo=bar
    cli2 cli2.test_node.example_function foo=bar

Your challenge is to understand why ;)
