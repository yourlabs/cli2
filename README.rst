.. image:: https://yourlabs.io/oss/cli2/badges/master/pipeline.svg
   :target: https://yourlabs.io/oss/cli2/pipelines
.. image:: https://codecov.io/gh/yourlabs/cli2/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/yourlabs/cli2
.. image:: https://img.shields.io/pypi/v/cli2.svg
   :target: https://pypi.python.org/pypi/cli2

cli2: Python Automation Framework
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A Python command line and Ansible Action plugin framework that loves meta
programming: do less and get more out of it, perfect for many kinds of DevOps
gigs to automate everything.

Batteries included, all of which are useful on their own:

- beautiful CLI alternative to click, but much less verbose, allowing more
  creative design patterns without any boilerplate thanks to introspection
- which comes with a Sphinx extension to extensively document your CLIs
- magic 12-factor configuration library
- extremely beautiful structlog configuration for colorful and readable logging
- httpx client wrapper that handles all kind of retries, data masking...
- magic ORM for HTTP resources based on that client
- Ansible Action plugin library with all the beautiful logging and a rich
  testing library so that you can go straight to the point in pytest
- a good old fcntl based locking
- a command line to run any python function over a beautiful CLI

`Documentation available on RTFD <https://cli2.rtfd.io>`_.
