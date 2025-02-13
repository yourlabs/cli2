import inspect
import textwrap


def cmd(*args, **overrides):
    """Set the overrides for a command."""
    def wrap(cb):
        cb = cb.__func__ if inspect.ismethod(cb) else cb
        if 'doc' in overrides:
            overrides['doc'] = textwrap.dedent(overrides['doc']).strip()
        cb.cli2 = overrides
        return cb

    if args and not overrides:
        return wrap(args[0])

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


def hide(*names):
    def wrap(cb):
        for name in names:
            cb = arg(name, hide=True)(cb)
        return cb
    return wrap
