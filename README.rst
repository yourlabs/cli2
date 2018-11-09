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
        clilabs help django
        clilabs clilabs.django:list auth.user
        clilabs django:list auth.user  # also works
        # refer to the root one
        clilabs ~django.db.models:somefunc somearg some=kwarg

Demo::

    $ clilabs debug ~your.mod:yourfunc -a --b --something='to see' how it=parses
    Could not import your.mod
    Args: ('how',)
    Kwargs: {'it': 'parses'}
    Context args: ['a', 'b']
    Context kwargs: {'something': 'to see'}

Moar in tutorial.md

Making your own command
~~~~~~~~~~~~~~~~~~~~~~~

Add to your setup.py::

    entry_points={
        'console_scripts': [
            'yourcmd = yourpkg.cli:cli',
        ],
    },


Add in yourpkg/cli.py::

    '''Your documentation that shows by default:

        yourcmd somefunc ...
    '''
    import clilabs

    def cli(*argv):
        argv = list(argv) if argv else ['help', 'yourpkg.cli']
        cb = clilabs.modfuncimp(*clilabs.funcexpand(argv[0], 'yourpkg.cli'))
        args, kwargs = clilabs.expand(*argv[1:])
        return cb(*args, **kwargs)

    def main(...):
        '''Put your help text, that will show when the
        user runs the command without argument.'''
