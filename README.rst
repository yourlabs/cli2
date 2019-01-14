cli2: unfrustrating python CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes I just want to execute a python callback and pass args/kwargs on the
CLI, and not have to define any custom CLI entry point of any sort, nor change
any code, typically when automating stuff, cli2 unfrustrates me::

   cli2 yourmodule.yourcallback somearg somekwarg=foo

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
