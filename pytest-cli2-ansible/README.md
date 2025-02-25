# pytest-cli2-ansible

Install this package to get the playbook fixture from cli2.ansible.

Having that in the main package broke py.test for anyone who didn't have the
optional dependencies such as httpx and ansible.

```
Traceback (most recent call last):
  File "/home/thomas/code/jockiz/backend/djockiz/venv/bin/pytest", line 8, in <module>
    sys.exit(console_main())
             ~~~~~~~~~~~~^^
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/_pytest/config/__init__.py", line 201, in console_main
    code = main()
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/_pytest/config/__init__.py", line 156, in main
    config = _prepareconfig(args, plugins)
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/_pytest/config/__init__.py", line 341, in _prepareconfig
    config = pluginmanager.hook.pytest_cmdline_parse(
        pluginmanager=pluginmanager, args=args
    )
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/pluggy/_hooks.py", line 513, in __call__
    return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
           ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/pluggy/_manager.py", line 120, in _hookexec
    return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
           ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/pluggy/_callers.py", line 139, in _multicall
    raise exception.with_traceback(exception.__traceback__)
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/pluggy/_callers.py", line 122, in _multicall
    teardown.throw(exception)  # type: ignore[union-attr]
    ~~~~~~~~~~~~~~^^^^^^^^^^^
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/_pytest/helpconfig.py", line 105, in pytest_cmdline_parse
    config = yield
             ^^^^^
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/pluggy/_callers.py", line 103, in _multicall
    res = hook_impl.function(*args)
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/_pytest/config/__init__.py", line 1140, in pytest_cmdline_parse
    self.parse(args)
    ~~~~~~~~~~^^^^^^
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/_pytest/config/__init__.py", line 1494, in parse
    self._preparse(args, addopts=addopts)
    ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/_pytest/config/__init__.py", line 1381, in _preparse
    self.pluginmanager.load_setuptools_entrypoints("pytest11")
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/pluggy/_manager.py", line 421, in load_setuptools_entrypoints
    plugin = ep.load()
  File "/usr/lib/python3.13/importlib/metadata/__init__.py", line 179, in load
    module = import_module(match.group('module'))
  File "/usr/lib/python3.13/importlib/__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1310, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 488, in _call_with_frames_removed
  File "<frozen importlib._bootstrap>", line 1387, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1360, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1331, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 935, in _load_unlocked
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/_pytest/assertion/rewrite.py", line 184, in exec_module
    exec(co, module.__dict__)
    ~~~~^^^^^^^^^^^^^^^^^^^^^
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/cli2/ansible/__init__.py", line 2, in <module>
    from .action import (
    ...<5 lines>...
    )
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/_pytest/assertion/rewrite.py", line 184, in exec_module
    exec(co, module.__dict__)
    ~~~~^^^^^^^^^^^^^^^^^^^^^
  File "/home/thomas/code/jockiz/backend/djockiz/venv/lib/python3.13/site-packages/cli2/ansible/action.py", line 12, in <module>
    from ansible.plugins.action import ActionBase
ModuleNotFoundError: No module named 'ansible'
```
