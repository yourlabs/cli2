cli2 cli
========

You probably won't need this, unless you want to reverse engineer Python
library from the command line in a beautful way.

Initially, cli2 was supposed to just bring Python callables on the CLI without
even a single line of code::

    cli2 path.to.your.callable arg1 kwarg1=value

This command was implemented again in this 10th rewrite of the CLI engine
extracted from another repo, however this implementation features something
pretty funny: cli2 is a Group subclass which overrides the default Group
implementation based on the first argument passed on the command line.

Basically, when you call ``cli2 path.to.module``, it will load a Group of name
``path.to.module`` which whill load one Command per callable in
``path.to.module``.

When you call ``cli2 path.to.function`` it will execute the function.

As a result, these three commands are strictly equivalent::

    cli2 cli2.examples.obj2 nested
    cli2 cli2.examples.obj2.nested

That is because cli2 generates a group with every member of the previous group!

See for yourself with::

    cli2 help cli2

Or just::

    cli2 cli2

Because cli2.test_node is not a callable but a module, cli2's cli2 CLI created
a command Group on the fly with the module and added every callable member as
command.

When you call a group on the command line, it displays help by default to drive
the user.
