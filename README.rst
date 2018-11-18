clitoo: execute python callables from CLI too !
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes I want to execute a python callback with some args on the command
line, but i get frustrated that it always requires to wrap my command in a
wrapper of some sort or do something more than, just call a parameterized
callback from the CLI.

Clitoo unfrustrates me.

Install::

$ pip install clitoo

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
