"""
Basic test script

Another test to do is to run, in two terminals:

- python tests/lock.py 15
- python tests/lock.py
"""
import cli2
import mock


def test_non_blocking(tmp_path):
    lock1 = cli2.Lock(tmp_path / 'lock', blocking=False, prefix="a")
    lock1.log = mock.Mock()
    lock2 = cli2.Lock(tmp_path / 'lock', blocking=False)
    lock2.log = mock.Mock()
    with lock1:
        assert lock1.acquired

        lock1.log.debug.assert_called_once_with('Waiting')
        lock1.log.info.assert_called_once_with('Acquired')

        with lock2:
            assert not lock2.acquired

            lock2.log.debug.assert_called_once_with('Waiting')
            lock2.log.info.assert_called_once_with(
                'Not acquired but non blocking: proceeding',
            )
        lock2.log.debug.assert_called_with('Releasing')
        lock2.log.info.assert_called_with('Released')
    lock1.log.debug.assert_called_with('Releasing')
    lock1.log.info.assert_called_with('Deleted')


def test_log(tmp_path):
    path = tmp_path / 'foo'
    locker = cli2.Lock(path, prefix='hello')
    assert locker.log._context == dict(
        blocking=True,
        prefix='hello',
        lock_path=path,
    )
