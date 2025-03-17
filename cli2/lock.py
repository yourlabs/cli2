"""
Prevent multiple processes from doing the same operation on a host, using good
old Linux fnctl locking.

fcntl's ``flock`` is a great choice to prevent deadlocks if/when your process
crashes because the system will release any locks of a process when it dies.
``man fcntl`` for details.

Anyway, we provide a Lock class that acts as a context manager for both
blocking and non-blocking fcntl locks.

It's especially useful to orchestrate Ansible Action plugins.

Blocking locks
--------------

Consider this little program:

.. code-block:: python

    import cli2
    import os
    os.environ['LOG_LEVEL'] = 'DEBUG'
    with cli2.Lock('/tmp/mylock') as lock:
        input('say hello')

- Run it in a first terminal: it will log "Acquired" and show the "say hello"
  input.
- Run it in another terminal: it will log "Waiting"
- Type enter in the first terminal: it will release the lock and exit
- Then the second terminal will log "Acquired" and display the say hello input

You got this: two programs cannot enter the same blocking lock at the same
time.

Non blocking locks
------------------

You're starting a bunch of processes that potentially want to do the same thing
at the same time, ie. download a file to cache locally prior to sending it.

Only one process must do the caching download, the first one that gets the
lock, all others will sit there and wait.

This is possible with a non-blocking lock that we later convert into a blocking
lock.

.. code-block:: python

    with cli2.Lock('/tmp/mylock', blocking=False) as lock:
        if lock.acquired:
            # we got the lock, proceed to downloading safely
            do_download()
        else:
            # couldn't acquired the lock because another process got it
            # let's just wait for that other process to finish by converting
            # the non-blocking lock into a blocking one
            lock.block()

    # all processes can safely process to uploading
    do_upload()
"""
import fcntl
import functools
import os
from pathlib import Path


class Lock:
    """
    fcntl flock context manager, blocking and non blocking modes

    In doubt? set :envvar:`LOG_LEVEL` to ``DEBUG`` and you will see exactly
    what's happening.

    .. py:attribute:: lock_path

        Path to the file that we're going to use with flock.

    .. py:attribute:: blocking

        If True, the locker automatically blocks. Otherwise, you need to check
        :py:attr:`acquired` and call :py:meth:`block` yourself.

    .. py:attribute:: prefix

        Arbitrary string that will be added to logs.
    """

    def __init__(self, lock_path, blocking=True, prefix=None):
        self.lock_path = Path(lock_path)
        self.blocking = blocking
        self.acquired = True
        self.prefix = prefix or ''

    @functools.cached_property
    def log(self):
        from .log import log
        return log.bind(
            blocking=self.blocking,
            prefix=self.prefix,
            lock_path=self.lock_path,
        )

    def block(self):
        """ Basically converts a non-blocking lock into a blocking one """
        self.blocking = True
        self.acquire()

    def __enter__(self):
        self.log.debug('Waiting')
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.fp = self.lock_path.open('w+')

        if self.blocking:
            self.acquire()
            return self

        try:
            fcntl.flock(
                self.fp.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except BlockingIOError:
            self.log.info('Not acquired but non blocking: proceeding')
            self.acquired = False
        else:
            self.log.info('Acquired')
        return self

    def __exit__(self, _type, value, tb):
        self.log.debug('Releasing')
        self.release()

    def acquire(self):
        fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX)
        self.log.info('Acquired')

    def release(self):
        if self.acquired or not self.blocking:
            fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
            self.fp.close()
            self.log.info('Released')

        if self.acquired:
            try:
                os.unlink(self.lock_path)
            except FileNotFoundError:
                pass  # already deleted, or locked by another process
            else:
                self.log.info('Deleted')
