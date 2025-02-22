import cli2, os, time, sys
os.environ['LOG_LEVEL'] = 'DEBUG'
with cli2.Lock('/tmp/mylock', blocking=False) as lock:
    if lock.acquired:
        time.sleep(int(sys.argv[1]))
    else:
        print('Waiting for the other process to finish sleeping ...')
        lock.block()
