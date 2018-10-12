Try with your own command first, put this in example.py:

```
def main(*args, **kwargs):
    print(f'Args: {args}')
    print(f'Kwargs: {kwargs}')
```

Note that you can also use the example.py at the root of the repo for testing
purposes.

You invoke your own functions by defining the main function in a python module
that takes args and kwargs:

```
$ clilabs example.main somearg somekwarg=1
```

Note that you can either omit `:main` that is the default,
either target a callable:

```
$ clilabs example:SomeClass.some_attr.somestaticmethod
```

If an argument starts with `-`, it will be available with in the context object
you can import from clilabs. Change example.py to the following:

```
def main(*args, **kwargs):
    print(f'Args: {args}')
    print(f'Kwargs: {kwargs}')

    from clilabs import context
    print(f'Context args: {context.args}')
    print(f'Context kwagrs: {context.kwargs}')
```

Now try:

```
$ clilabs your.module --noinput -c=2
```

Or fiddle around with the debug builtin command:

```
$ clilabs debug help -a --b=2 c=3 d
Callable: <function help at 0x7f888647ef28>
Callable path: /home/jpic/src/clilabs/clilabs/builtins.py
Args: ('d',)
Kwargs: {'c': '3'}
Context args: ['a']
Context kwargs: {'b': '2'}
```

The tradeoff is that you cannot use space to delimit key from value because
that would confuse the lexer which wouldn't be able to distinguish value from
un-named argument:

```
# results in context.args == ['c'] and args == ['somearg']
# NOT in context['c'] == 'somearg'
$ clilabs your.module -c somearg
```

When it finds only a `-` alone then it will read stdin for a value:

```
$ echo bar | clilabs example -
```

Help is based on docstrings:

```
# docstring of function
$ clilabs clilabs.builtins:help your.mod:main

# since help is clilabs.builtins, no need to prefix with clilabs:
$ clilabs help clilabs.django
```

Pycli also bundles a nice bunch of functions for Django, for now it has a
django submodule that defines a bunch of CLI functions:

```
# find the content for this variable in your project manage.py
# because automated software should be available automatically
# changing INSTALLED_APPS is considered a manual operation
$ export DJANGO_SETTINGS_MODULE=your.settings

# you will probably run this from your directory parent to manage.py:
$ clilabs clilabs.django:create auth.user username=pony is_superuser=1

# django is a builtin module, you can use + instead of clilabs.:
$ clilabs +django:create auth.user username=pony is_superuser=1

# for idempotent create, add field names to use as reference
$ clilabs +django:create auth.user username=pony is_superuser=1 username

# i just checked and chpasswd command in django supports only interactive
$ clilabs +django:chpasswd yourpassword username=pony

# supports stdin too with -
$ echo yourpassword | +django:chpasswd - username=pony

# find stuff:
$ clilabs +django:ls auth.user username is_superuser
| pk | username | is_superuser |
| 1  | pony     |     True     |
| 2  | ninja    |     False    |

# kwargs are passed to filter
$ clilabs +django:ls auth.user username is_superuser=true
| pk | username | is_superuser |
| 1  | ninja    |     True     |

# you can also delete
$ clilabs +django:delete auth.user username=lol123

# count supports filters too
$ clilabs clilabs.django:count is_superuser=true
1

# delete stuff, would be nicer with --noinput
$ clilabs clilabs.django:delete auth.user username=pony --noinput
1

# you can use other models
$ clilabs +django:create sites.site name='awesome site' domain=awesome.com
$ clilabs +django:list admin.logentry
$ clilabs +django:detail auth.groups pk=1

# and of course your own apps:
$ clilabs yourapp.cli:dosomething with_that_arg with_that_kwarg=1 --noinput --othercontextarg=1
```

## Why not use a management command ?

**Because automation software should be automatically made available in an
automated way.**

That means, having to add it to INSTALLED_APPS is: no because it's a manual
operation.

## Why is it not available as management command ?

Because we need to break out of the framework's inversion of control to make
such a rich user experience from the command line: with dynamic options.

## Why not use click ?

I really wonder how to use click to work out with this weird cli.

## Do you have crazy ideas for new django functions ?

Always, why not being able to run a forms on the command line given a dotted
import path, both in interactive, and non interactive mode ?

Or, why not provision a model from a file tree of YAML files to replace
loaddata ?

Last time I needed those features, I passed, but it's over now.
