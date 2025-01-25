import inspect


def cmd(**overrides):
    """Set the overrides for a command."""
    def wrap(cb):
        cb = cb.__func__ if inspect.ismethod(cb) else cb
        cb.cli2 = overrides
        return cb
    return wrap


def arg(name, **kwargs):
    """Set the overrides for an argument."""
    def wrap(cb):
        cb = cb.__func__ if inspect.ismethod(cb) else cb
        overrides = getattr(cb, 'cli2_' + name, None)
        if overrides is None:
            try:
                setattr(cb, 'cli2_' + name, {})
            except AttributeError:
                setattr(cb.__func__, 'cli2_' + name, {})
        try:
            overrides = getattr(cb, 'cli2_' + name)
        except AttributeError:
            overrides = getattr(cb.__func__, 'cli2_' + name)
        overrides.update(kwargs)
        return cb
    return wrap


def factories(*args, **args_overrides):
    args_overrides.setdefault('self', '__init__')
    args_overrides.setdefault('cls', '__class__')

    def _(cls):
        for key, value in args_overrides.items():
            arg(key, factory=value)(cls)

        for name, obj in inspect.getmembers(cls):
            if not inspect.isfunction(obj) and not inspect.ismethod(obj):
                continue
            obj = getattr(obj, '__func__', obj)
            specials = dict(
                __init__=lambda *a, **k: cls(*a, **k),
                __class__=lambda *a, **k: cls,
            )
            argspec = inspect.getfullargspec(obj)
            for key, value in args_overrides.items():
                if key in argspec.args:
                    callback = None
                    if isinstance(value, str) and value not in specials.keys():
                        callback = getattr(cls, value)
                    if not callback:
                        callback = specials.get(value, value)
                    arg(key, factory=callback)(obj)
        return cls

    if args:
        # simple @cli2.factories call without argument
        return _(args[0])

    return _
