cli2.cli Sphinx Documentation
=============================

Add ``'cli2.sphinx'`` to your extensions in ``docs/conf.py``, then use the
following directive to generate full documentation for your CLI:
``.. cli2:auto:: cli2-example``

Then, you can link to your commands and arguments as such:

- ``:cli2:grp:`cli2-example```
- ``:cli2:cmd:`cli2-example get```
- ``:cli2:arg:`cli2-example get base_url```

Shown in :doc:`example`
