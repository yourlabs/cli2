djcli is the package , a new CLI [under design phase](https://yourlabs.io/oss/djcli), it is a simple python package, that provides a command with name `djcli`, to do more with Django on the CLI:

```
$ pip install djcli

# find the content for this variable in your project manage.py
$ export DJANGO_SETTINGS_MODULE=your.settings

# you will probably run this from your directory parent to manage.py:
$ djcli create auth.user username=pony is_superuser=1

# i just checked and chpasswd command in django supports only interactive
$ djcli chpasswd /path/to/password username=pony

# supports stdin too with -
$ echo yourpassword | djcli chpasswd - username=pony

# find stuff:
$ djcli list auth.user username is_superuser
| pk | username | is_superuser |
| 1  | pony     |     True     |
| 2  | ninja    |     False    |

# and filter
$ djcli list auth.user username is_superuser=true
| pk | username | is_superuser |
| 1  | ninja    |     True     |

# count supports filters too
$ djcli count is_superuser=true
1

# delete stuff, would be nicer with --noinput
$ djcli delete auth.user username=pony --noinput
1

# you can use other models
$ djcli create sites.site name='awesome site' domain=awesome.com
```

## Why not add it to INSTALLED_APPS ?

**Because automation software should be automatically made available in an automated way.**

Don't listen to people who tell you otherwise :D

## Why is it not available as management command ?

Because we need to break out of the framework's inversion of control to make such a rich user experience from the command line: with dynamic options.

## Do you have crazy ideas ?

Always, why not being able to run a forms on the command line given a dotted import path, both in interactive, and non interactive mode ?

Or, why not provision a model from a file tree of YAML files to replace loaddata ?

Last time I needed those features, I passed, but it's over now.

## When is stable release ?

Nobody cares about the stable release of djcli, not even me.