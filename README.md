# Automate model management with the CRUD CLI for models: djclicrud

This document sets the specifications for a new CLI.


```
$ pip install djclicrud

# find the content for this variable in your project manage.py
$ export DJANGO_SETTINGS_MODULE=your.settings

# you will probably run this from your directory parent to manage.py:
$ djclicrud create auth.user username=pony is_superuser=1

# i just checked and chpasswd command in django supports only interactive
$ echo newpassword | djclicrud chpasswd username=pony

# now let's rock, default is command is not create but list:
$ djclicrud auth.user username is_superuser
| pk | username | is_superuser |
| 1  | pony     |     True     |
| 2  | ninja    |     False    |

# you can also use filter
$ djclicrud auth.user username is_superuser=false
| pk | username |
| 1  | pony     |

# and do a delete
$ djclicrud delete auth.user username=pony --noinput
```

If you're running this in a container, and that your project has a setup.py, 
chances are your environment variable DJANGO_SETTINGS_MODULE is already set.