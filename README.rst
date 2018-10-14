clilabs: the python CLI that gets things done.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sometimes I want to execute a python callback with some args on the command
line, but i get frustrated that it always requires to wrap my command in a
wrapper of some sort. Clilabs unfrustrates me.

Install::

$ pip install clilabs

Help::

    $ clilabs
    clilabs automates python callables parametered calls.

    Things starting with - will arrive in clilabs.context.

    Examples:

        clilabs help your.mod:main
        clilabs debug your.mod -a --b --something='to see' how it=parses
        clilabs your.mod:funcname with your=args
        clilabs help clilabs.django
        clilabs clilabs.django:list auth.user
        clilabs +django:list auth.user  # also works

Demo::

    $ clilabs debug your.mod:yourfunc -a --b --something='to see' how it=parses
    Could not import your.mod
    Args: ('how',)
    Kwargs: {'it': 'parses'}
    Context args: ['a', 'b']
    Context kwagrs: {'something': 'to see'}

Moar in tutorial.md
