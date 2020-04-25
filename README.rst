cli2: another CLI lib for Python
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Break free from the POSIX standard for more fluent CLIs, by exposing simple
Python functions or objects with a minimalist argument typing style, or
building your own command try during runtime.

CLI Usage for users
===================

This section describes the parsing logic, it targets audience that's using cli2
via another tool, or considering to make their tool's CLI with cli2.

Suppose you have a function with one argument as such:

.. code-block:: python

    def yourcmd(a):
        """Your own command"""


Then you can set the "a" argument either "directly" or "namedly" like a keyword
argument::

    yourcmd foo       # a="foo"
    yourcmd a=foo     # also a="foo"

Command line will parse strings without any type casting unless type annotation
is set on the argument or it has a default value that's not None.

Argument aliases are supported principally for booleans, but work with other
types too:

.. code-block:: python

    @cli2.option("age", alias="-a")
    @cli2.option("debug", alias="-d")
    def yourcmd(age, debug=False):
        # ...

In which case you can specify arguments by alias::

    yourcmd -a=12 -d   # yourcmd(a=12, debug=True)

List parsing
------------

To enable cli2 casting, use type annotations, for example:

.. code-block:: python

    def yourcmd(a: list):
        # ....

In this case, the first parsed argument will be casted as first list item if
passed "directly"::

    yourcmd somearg     # a=["somearg"]

For multi-item lists, you can build a list of strings by repeating the argument
or with the simple list syntax, resort to json syntax for more type support::

    yourcmd a=1 a=2    # a=["1", "2"]
    yourcmd '[a, 3]'   # a=["a", "b", "3"]
    yourcmd '["a", 3]' # a=["a", 3]
    yourcmd '[1]'      # a=[1] because json is tried first

Dict parsing
------------

Dict arg parsing is enabled with the dict type annotation, for example:

.. code-block:: python

    def yourcmd(a: dict):
        # ....

For a dict value, you can build a dict of strings using a dotted syntax::

    yourcmd a.b=c a.2=3     # a={"b": "c", "2": "3"}

Or, use a simple string-dict syntax or JSON for more types::

    yourcmd '{a: b, c: 1}'            # a={"a": "b", "c": "1"}
    yourcmd '{"a": "b", "c": 1}'      # a={"a": "b", "c": 1}
    yourcmd '{"a": "b", "c": 1}'      # a={"a": "b", "c": 1}

Extra
-----

One feature important for me is to be able to code wrapper for other command
lines. That means that unrecognized arguments will not cause an error to be
thrown, but they will be added to a list called ``extra`` so that I can pass
them on to an underlying command (such as ansible-playbook which accepts a
bunch).

Framework
=========

Arguments
---------

An interresting point is that you can override the default Argument class and
override how the argument is casted in Python as such:

.. code-block:: python

    def foo(ages):
        pass

    class AgesArgument(Argument):
        def cast(self, value):
            return [int(i) for i in value.split(',')]

    cmd = Command(foo, arguments=[AgesArgument('ages', '-a')])
    cmd.parse('-a=1,2')
    cmd.vars['ages'] == [1, 2]

As you can see, we have implemented custom parsing of a value. Actually an
alias is not necessary for that specific purpose:

.. code-block:: python

    cmd = Command(foo, arguments=[AgesArgument('ages')])
    cmd.parse('ages=1,2')
    cmd.vars['ages'] == [1, 2]

Note that when you instanciate an Argument for a callable arg it becomes
non-positional:

.. code-block:: python

    def foo(a, b=None): pass
    cmd = Command(foo, arguments=[AgesArgument('ages')])
    cmd.parse('c', '-a=3')
    assert cmd.vars['a'] == 3
    assert cmd.vars['b'] == 'c'

At this point, it should be pretty clear that you are free to implement any
kind of option parsing and casting at a per-option level.

Actually, you can even go down this road and override ``Command.parse`` for a
specific command, and implement a completely different parsing logic from other
commands, this should work well as long as you're will to write a lot of little
tests.

Another way is to use an override:

.. code-block:: python

    def foo(ages):
        pass
    foo.cli2_ages = dict(
        alias='-a',
        cast=lambda v: [int(i) for i in value.split(',')]
    )

The advantage of that way is that you don't need to import cli2, and as such
you may leave it as an optional dependency to your package.

Sometimes I just want to execute a python callback and pass args/kwargs on the
CLI, and not have to define any custom CLI entry point of any sort, nor change
any code, typically when automating stuff, cli2 unfrustrates me::

   cli2 yourmodule.yourcallback somearg somekwarg=yourcmd

Sometimes I just want to define a new command and expose all callables in a
module and I can't just do it with a one-liner. cli2 unfrustrates me again:

.. code-block:: python

   console_script = cli2.ConsoleScript(__doc__).add_module('mymodule')
   # then i add console_script entrypoint as such: mycmd = mycmd.console_script

I also like when readonly commands are in green, writing commands in yellow and
destructive commands in red, I find the commands list in the help output more
readable, and directive for new users of the CLI:

.. code-block:: python

   @cli2.config(color=cli2.RED)
   def challenge(dir):
      '''The challenge command dares you to run it.'''
      os.exec('rm -rf ' + dir)

Of course then there's all this code I need to have coverage for and I'm
`still
<https://pypi.org/project/django-dbdiff/>`_ so lazy that I still
`don't write most of my test code myself
<https://pypi.org/project/django-responsediff/>`_, so I throwed an autotest
function in cli2 ("ala" dbunit with a personal touch) that I can use as such:

.. code-block:: python

   @pytest.mark.parametrize('name,command', [
       ('cli2', ''),
       ('help', 'help'),
       ('help_debug', 'help debug'),
       # ... bunch of other commands
       ('debug', 'debug cli2.run to see=how -it --parses=me'),
   ])
   def test_cli2(name, command):
       cli2.autotest(
           f'tests/{name}.txt',
           'cli2 ' + command,
       )

You should be able tho pip install cli2 and start using the cli2 command, or
cli2.ConsoleScript to make your own commands.

.. image:: https://asciinema.org/a/221137.svg
   :target: https://asciinema.org/a/221137

Check `djcli, another cli built on cli2
<https://pypi.org/project/djcli>`_.
