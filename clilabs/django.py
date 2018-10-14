"""Builtin callables for Django framework.

It requires DJANGO_SETTINGS_MODULE env var, and does not require to be in
INSTALLED_APPS because automation software should be made automatically
available and adding to INSTALLED_APPS is a manual step.
"""
import os
import traceback
import sys

import django
from django.apps import apps

import clilabs
from tabulate import tabulate

try:
    django.setup()
except Exception:
    print('Setting up django has failed !')
    print('DJANGO_SETTINGS_MODULE env var not set !')
    if 'DJANGO_SETTINGS_MODULE' in os.environ:
        print(f'DJANGO_SETTINGS_MODULE={os.getenv("DJANGO_SETTINGS_MODULE")}')
        traceback.print_exc()


def _modeldata(obj, keys=None):
    keys = keys or [
        k for k in obj.__dict__.keys()
        if not k.startswith('_')
    ]

    return {k: getattr(obj, k) for k in keys}


def _printqs(qs, keys=None):
    keys = keys or None
    header = sorted(list(_modeldata(qs[0], keys).keys()))
    print(tabulate([header] + [
        [getattr(i, k) for k in header]
        for i in qs
    ]))


def create(modelname, *args, **kwargs):
    """Idempotent create function.

    First argument must be model name, for apps.get_model.
    With only keyword arguments, it will pass them to create().
    If you pass arguments, it will use update_or_create, passing
    any keyword argument name as defaults to update_or_create
    instead of kwarg.

    # Create a user, not idempotent
    playlabs +django:create auth.user username=foo email=joe@example.com

    # Create or update a user based on email, idempotent yay !
    playlabs +django:create auth.user email username=foo email=joe@example.com

    # oh, and with settings.* support for your model swapping fun hacks ;)
    playlabs +django:create settings.AUTH_USER_MODEL ...
    """
    if modelname.startswith('settings.'):
        from django.conf import settings
        modelname = getattr(settings, modelname.split('.')[1])
    model = apps.get_model(modelname)

    if not args:
        obj = model.objects.create(**kwargs)
        created = True
    else:
        defaults = {}
        for key, value in kwargs.copy().items():
            if key not in args:
                defaults[key] = kwargs.pop(key)
        obj, created = model.objects.update_or_create(defaults, **kwargs)

    print(tabulate([
        (k, v)
        for k, v in _modeldata(obj).items()
    ]))


def ls(modelname, *args, **kwargs):
    """Search models

    kwargs are passed to filter.
    It shows all fields by default, you can restrict them with args.

    Show username and email for superusers:

    clilabs +django:ls auth.user is_superuser=1 username email
    """

    model = apps.get_model(modelname)
    models = model.objects.filter(**kwargs)
    if not models:
        print('No result found !')
        sys.exit(0)

    _printqs(models, args)


def delete(modelname, **kwargs):
    model = apps.get_model(modelname)
    qs = model.objects.filter(**kwargs)
    if not qs:
        print('No model to delete !')
        return
    _printqs(qs)
    count = len(qs)
    qs.delete()
    print(f'Deleted {count} objects')


def detail(modelname, *args, **kwargs):
    """Print detail for a model.

    kwargs are passed to filter()

    clilabs +django:detail pk=123
    """
    model = apps.get_model(modelname)
    obj = model.objects.get(**kwargs)
    print(tabulate([
        (k, v)
        for k, v in _modeldata(obj).items()
        if k in args or not args
    ]))


def chpasswd(password, **kwargs):
    """Change the password for user.

    It takes the password as argument, that you can use `-` for stdin.
    All kwargs will be passed to get()

    Example:

        clilabs +django:chpasswd username=... thepassword
        echo thepassword | clilabs +django:chpasswd username=... -
    """

    from django.conf import settings
    model = apps.get_model(settings.AUTH_USER_MODEL)
    user = model.objects.get(**kwargs)
    user.set_password(password)
    user.save()
    print('Password updated !')


def main(*args, **kwargs):
    if not args:
        print('For help, run clilabs help +django')

    cb = clilabs.funcimp(args[0])
    return cb(*args[1:], **kwargs)
