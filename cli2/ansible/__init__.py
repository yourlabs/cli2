# flake8: noqa
"""
Wrapping all imports in a try/except because pytest always tries to import
this even when we're using cli2 without ansible
"""
try:
    from .action import (
        ansi_escape,
        Option,
        AnsibleError,
        AnsibleOptionError,
        ActionBase,
    )
    from .variables import Variables
except ImportError:
    pass
