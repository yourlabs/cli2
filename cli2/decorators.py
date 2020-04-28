

def cmd(**overrides):
    def wrap(cb):
        cb.cli2 = overrides
        return cb
    return wrap


def arg(name, **kwargs):
    def wrap(cb):
        overrides = getattr(cb, 'cli2_' + name, None)
        if overrides is None:
            setattr(cb, 'cli2_' + name, {})
        overrides = getattr(cb, 'cli2_' + name)
        overrides.update(kwargs)
        return cb
    return wrap
