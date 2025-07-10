#!/usr/bin/env python

import cli2


def yourcmd(somearg, x=None, verbose: bool = False, *args, foo=None, **kwargs):
    """
    Your own command.

    - Some List
    - Other Item

    Example code:

        example indented code

    :param somearg: It's some string argument that this function will return
    """
    return (somearg, x, verbose, args, foo, kwargs)


if __name__ == '__main__':
    # to try with python-fire:
    # import fire; fire.Fire(yourcmd)
    import os
    posix = bool(os.getenv('POSIX', '1'))
    cli2.Command(yourcmd, posix=posix).entry_point()
