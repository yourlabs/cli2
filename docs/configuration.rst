Configuration
~~~~~~~~~~~~~

.. automodule:: cli2.configuration
   :members:


Example
-------

.. code-block:: python

    import cli2

    cli2.cfg.questions['FOO'] = 'What is your FOO?'

    print(f'Foo={cli2.cfg["FOO"]}')
    print(f'Bar={cli2.cfg["BAR"]}')

Session:

.. code-block::

    $ python cli2/examples/conf.py
    What is your FOO?
    > dunno

    Confirm value of:
    dunno
    (Y/n) >
    Appended to /home/jpic/.profile:
    export FOO=dunno
    Foo=dunno

    BAR
    > woot?

    Confirm value of:
    woot?
    (Y/n) >y
    Appended to /home/jpic/.profile:
    export BAR='woot?'
    Bar=woot?

    $ python cli2/examples/conf.py
    Foo=dunno
    Bar=woot?
