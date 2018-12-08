cli2: python callables from CLI too !
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install cli2 ie.::

    $ pip3 install --user cli2

Cli2 can be used as a generic command line to execute callbacks and print
docstrings::

    $ cli2 --debug your.callback
    $ cli2 your.callback arg0 kwarg0=aoeu

, or as a CLI framework: first give it a name in the
``console_scripts`` entry point like ``yourapp`` and point it to
``cli2:console_script``, example using `setupmeta
<https://github.com/zsimic/setupmeta>`_'s ``entry_points.ini``::

    [console_scripts]
    yourapp = cli2:console_script

Then register your commands easily, ie::

    [yourapp]
    # bind yourapp help to cli2.help
    yourapp help = cli2.help
    # bind yourapp run to yourapp.cli.run
    yourapp run = yourapp.cli.run
    # bind yourapp * to callbacks in yourapp.cli
    yourapp * = yourapp.cli

Help::

    Clitoo makes your python callbacks work on CLI too !

    This CLI can execute python callbacks with parameters.

    Clitoo recognizes 4 types of command line arguments:

    - lone arguments are passed as args
    - arguments with = are passed as kwargs
    - dashed arguments like -f arrive in context.args
    - dashed arguments like -foo=bar arrive in context.kwargs

    It doesn't matter how many dashes you put in the front, they are all
    removed.

    To use the context in your callback just import the clitoo context::

        from clitoo import context
        print(context.args, context.kwargs)

    Clitoo provides 2 builtin commands: help and debug. Any other first
    argument will be considered as the dotted path to the callback to import
    and execute.

    Examples:

    clitoo help your.mod.funcname
        Print out the function docstring.

    clitoo debug your.func -a --b --something='to see' how it=parses
        Dry run of your.mod with arguments, dump out actual calls.

    clitoo your.mod.funcname with your=args
        Call your.mod.funcname('with', your='args').


Demo::

    $ clitoo debug your.func -a --b --something='to see' how it=parses
    Could not import your.func nor clitoo.your.func
    Args: ('how',)
    Kwargs: {'it': 'parses'}
    Context args: ['a', 'b']
    Context kwargs: {'something': 'to see'}

Fallbacks
~~~~~~~~~

Clitoo will attempt to fallback on packages of its own. If it doesn't find the
`git.clone` callback from the `git` package, or doesn't find the `git` package
itself, it will find `clitoo.git.clone` which is a builtin command that we use
in CI.

Making your own command
~~~~~~~~~~~~~~~~~~~~~~~

See the djcli repository for an example of command that is packaged as
standalone, but it looks like::

	# Declare the following as CLI entry_point
	def cli():
	    clitoo.context.default_module = __name__
	    return clitoo.main()
