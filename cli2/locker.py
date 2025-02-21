import fcntl
import os


class Locker:
    def __init__(self, lock_path, blocking=True, prefix=None):
        self.lock_path = lock_path
        self.blocking = blocking
        self.acquired = True
        self.prefix = prefix or ''

    def display(self, msg):
        _ = []
        if self.blocking:
            _.append('[BLOCKING LOCK]')
        else:
            _.append('[NON BLOCKING LOCK]')
        if self.prefix:
            _.append(f'[{self.prefix}]')
        _.append(f'[{self.lock_path}]')
        _.append(f' {msg}')
        self.print(''.join(_))

    def print(self, msg):
        print(msg)

    def __enter__(self):
        self.display('Waiting')
        self.lock_path.parent.mkdir(parents=True, exists_ok=True)
        self.fp = self.lock_path.open('w+')

        if self.blocking:
            fcntl.flock(self.fp.fileno(), fcntl.LOCK_EX)
            self.display('Acquired')
            return self

        try:
            fcntl.flock(
                self.fp.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except BlockingIOError:
            self.display('Not acquired but non blocking: proceeding')
            self.acquired = False
        else:
            self.display('Acquired')
        return self

    def __exit__(self, _type, value, tb):
        self.display('Releasing')
        if self.acquired or not self.blocking:
            fcntl.flock(self.fp.fileno(), fcntl.LOCK_UN)
            self.fp.close()
            self.display('Released')

        if self.acquired:
            try:
                os.unlink(self.lock_path)
            except FileNotFoundError:
                pass  # already deleted, or locked by another process
            else:
                self.display('Deleted')
