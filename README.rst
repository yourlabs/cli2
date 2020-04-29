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

Getting Started
===============

Create a command from any callable:

.. code-block:: python

    def yourcmd():
        """Your own command"""

    cli = cli2.Command(yourcmd)

No entry point
--------------

If you don't want to use an entry point, you can execute your command as such
which will print the result:

.. code-block:: python

    # without entry_point, you can call yourself
    import sys
    print(cli(*sys.argv[1:]))

Even if you want to use an entry point, this kind of call can also be useful
for testing:

.. code-block:: python

    from your.module import cli

    def test_cli():
        # simulate command: yourcmd some thing
        assert cli('some', 'thing') == 'some result'

Entry point
-----------

You may also use the ``.entry_point`` attribute of ``cli2.Command`` or
``cli2.Group`` to define a command with the ``clis`` entry point by adding
something like that to your ``setup.py``:

.. code-block:: python

    entry_points={
        'console_scripts': [
            'yourcmd  = your.module:cli.entry_point',
        ],
    },

Command group
-------------

In the same fashing, you can create a command Group, and add Commands to it:

.. code-block:: python

    # create a command group
    cli = cli2.Group()

    # optionnaly, tell it to generate argument names with dashes
    cli = cli2.Group(posix=True)

    # and add yourcmd to it
    cli.add(yourcmd)

    # or with a decorator
    @cli.cmd
    def foo(): pass

    # decorator that can also override the Command attributes btw
    @cli.cmd(name='bar')
    def foo(): pass

    # or add a Command per callables of a module
    cli.load(your.module)
    # or by name
    cli.load('your.module')

    # and/or add from an object to create a Command per method
    cli.load(your_object)

Type-casting
------------

Type hinting is well supported, but you may also hack how arguments are casted
into python values at a per argument level, set the ``cli2_argname`` attribute
to attributes that you want to override on the generated Argument for
``argname``.

You could cast any argument with JSON as such:

.. code-block:: python

    @cli2.arg('x', cast=lambda v: json.loads(v))
    def yourcmd(x):
        return x

    cmd = Command(yourcmd)
    cmd(['[1,2]']) == [1, 2]  # same as CLI: yourcmd [1,2]

Or, override ``Argument.cast()`` for the ``ages`` argument:

.. code-block:: python

    @cli2.args('ages', cast=lambda v: [int(i) for i in v.split(',')])
    def yourcmd(ages):
        return ages

    cmd = Command(yourcmd)
    cmd(['1,2']) == [1, 2]  # same as CLI: yourcmd 1,2

If an argument is annotated with the list or dict type, then cli2 will use
json.loads to cast them to Python arguments, but be careful with spaces on your
command line: one sysarg goes to one argument::

    yourcmd ["a","b"]   # works
    yourcmd ["a", "b"]  # does not because of the space

However, space is supported as long as in the same sysarg:

.. code-block:: python

    subprocess.check_call(['yourcmd', '["a", "b"]')

Typable syntax
--------------

Arguments with the list type annotation are automatically parsed as JSON, if
that fails it will try to split by commas which is easier to type than JSON for
lists of strings::

    yourcmd a,b  # calls yourcmd(["a", "b"])

Keep in mind that JSON is tried first for list arguments, so a list of ints is
also easy::

    yourcmd [1,2]  # calls yourcmd([1, 2])

A simple syntax is also supported for dicts by default::

    yourcmd a:b,c:d  # calls yourcmd({"a": "b", "c": "d"})

The disadvantage is that JSON decode exceptions are swallowed, but by design
cli2 is supposed to make Python types more accessible on the CLI, rather than
being a JSON validation tool. Generated JSON args should always work though.

Boolean flags
-------------

Cast to boolean is already supported by type-hinting, or with json (see above
example), or with simple switches:

.. code-block:: python

    # manually do what posix=True would generate
    @cli2.arg('debug', alias=['-d', '--debug'], negate=['-nd', '--no-debug'])
    def yourcmd(debug=True):
        pass

Overriding Command and Argument classes
---------------------------------------

Overriding the Command class can be useful to override how the target callable
will be invoked. Example:

.. code-block:: python

    class YourThingCommand(cli2.Command):
        def call(self):
            self.target.is_CLI = True
            return self.target(*self.bound.args, **self.bound.kwargs)

    @cli2.cmd(cls=YourThingCommand)
    class YourThing:
        def __call__(self):
            pass

    cmd = Command(YourThing())  # will be a YourThingCommand

Overriding an Argument class can be useful if you want to heavily customize an
argument, here's an example with the age argument again:

.. code-block:: python

    class AgesArgument(cli2.Argument):
        def cast(self, value):
            # logic to convert the ages argument from the command line to
            # python goes in this method
            return [int(i) for i in value.split(',')]

    @cli2.arg('ages', cls=AgesArgument)
    def yourcmd(ages):
        return ages

    assert yourcmd('1,2') == [1, 2]

Edge cases
==========

Simple and common use cases were favored over rarer use cases by design. Know
the couple of gotchas and you'll be fine.

Args containing ``=`` when ``**kwargs`` is present
--------------------------------------------------

Simple use cases are favored over rarer ones when a callable has varkwargs.

When a callable has ``**kwargs`` as such:

.. code-block:: python

    def foo(x, **kwargs):
        pass

Then, arguments that look like kwargs will be attracted to the kwargs
argument, so if you want to call ``foo("a=b")`` then you need to call as such::

    foo x=a=b

Because the following will call ``foo(a='b')``, and fail because of missing
``x``, which is more often than not what you want on the command line::

    foo a=b

Now, even more of an edgy case when ``*args, **kwargs`` are used:

.. code-block:: python

    def foo(*args, **kwargs):
        return (args, kwargs)

Call ``foo("a", b="x")`` on the CLI as such::

    foo a b=x

**BUT**, to call ``foo("a", "b=x")`` on the CLI you will need to use an
asterisk with a JSON list as such::

    foo '*["a","b=x"]'

Admittedly, the second use case should be pretty rare compared to the first
one, so that's why the first one is favored.

For the sake of consistency, varkwarg can also be specified with a double
asterisk and a JSON dict as such::

    # call foo("a", b="x")
    foo a **{"b":"x"}

Calling with ``a="b=x"`` in ``(a=None, b=None)``
------------------------------------------------

The main weakness is that it's difficult to tell the difference between a
keyword argument, and a keyword argument passed positionnaly which value starts
with the name of another keyword argument. Example:

.. code-block:: python

    def foo(a=None, b=None):
        return (a, b)

Call ``foo(b='x')`` on the CLI like this::

    foo b=x

**BUT**, to call ``foo(a="b=x")`` on the CLI, you need to name the argument::

    foo a=b=x

Admitadly, that's a silly edge case. Protect yourself from it by always naming
keyword arguments ...

... Because the parser considers token that start with a keyword of a keyword
argument prioritary to positional arguments once the positional arguments have
all been bound.

Demo
====

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
