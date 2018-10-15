"""
Automate sentry-cli cooking for uploading sourcemaps.
"""
import glob
import os
import subprocess
import sys


def _run(cmd):
    print('+', ' '.join(cmd))

    proc = subprocess.Popen(
        cmd,
        stderr=subprocess.STDOUT,
        stdout=subprocess.PIPE,
    )

    try:
        outs, errs = proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, errs = proc.communicate()

    if outs:
        print(outs.decode('utf8'))
    if errs:
        print(errs.decode('utf8'))

    return proc.returncode


def _getenv(name):
    value = os.getenv(name)
    if not value:
        print(f'{name} not set, aborting')
        sys.exit(1)
    return value


def release_delete():
    """
    Equivalent to:

        sentry-cli releases delete $GIT_COMMIT

    Except your exit code will always be 0 (idempotent-ish).
    """
    version = _getenv('GIT_COMMIT')
    cmd = ['sentry-cli', 'releases', 'delete', version]
    _run(cmd)


def release_new():
    """
    Equivalent to:

        sentry-cli releases new -p $SENTRY_PROJECT $GIT_COMMIT
    """
    projects = _getenv('SENTRY_PROJECT')
    version = _getenv('GIT_COMMIT')

    cmd = ['sentry-cli', 'releases', 'new', version]
    for p in projects.split(' '):
        cmd += ['-p', p]

    return _run(cmd)


def release_set_commits():
    """
    Equivalent to:

        sentry-cli releases set-commits $GIT_COMMIT --commit $REPO@$GIT_COMMIT
    """
    repo = _getenv('REPO')
    version = _getenv('GIT_COMMIT')

    cmd = ['sentry-cli', 'releases', 'set-commits', version]
    cmd += ['--commit', f'{repo}@{version}']
    _run(cmd)


def release_upload_js(*dirs):
    """
    Equivalent to something like:

    for i in $(find $STATIC_ROOT -type f -name '*.js' ! -name '*.test.js'); do
      sentry-cli releases files $V upload $i $STATIC_URL/${i##$STATIC_ROOT}
    done

    However, it will recursively add directories passed as arguments.

    When it builds the url of the file, it will strip STATIC_ROOT, and prepend
    STATIC_URL: it doesn't have to be the STATIC_ROOT of your django project,
    you can run this in each app you want to upload sourcemaps for, since this
    step is only needed to get sourcemaps if, for example, your environment
    is being HTTP Basic auth and sentry can't download them by itself.
    """
    version = _getenv('GIT_COMMIT')
    static_url = _getenv('STATIC_URL')
    base_cmd = ['sentry-cli', 'releases', 'files', version, 'upload']

    curdir = os.getcwd()
    for d in dirs:
        os.chdir(d)
        for i in glob.iglob('**/*.js', recursive=True):
            _run(base_cmd + [i, os.path.join(static_url, i)])
    os.chdir(curdir)


def release_upload_sourcemaps(*dirs):
    """Equivalent to:

    for i in $(find $STATIC_ROOT -type f -name '*.js.map'); do
      sentry-cli releases files $GIT_COMMIT upload-sourcemaps --validate $i
    done
    """
    version = _getenv('GIT_COMMIT')
    static_url = _getenv('STATIC_URL')
    base_cmd = [
        'sentry-cli',
        'releases',
        'files',
        version,
        'upload-sourcemaps',
        '--validate'
    ]

    curdir = os.getcwd()
    for d in dirs:
        os.chdir(d)
        for i in glob.iglob('**/*.js.map', recursive=True):
            prefix = os.path.join(static_url, '/'.join(i.split('/')[:-1]))
            _run(base_cmd + ['--url-prefix', prefix, i])
    os.chdir(curdir)


def release_finalize():
    """Equivalent to:

    sentry-cli releases finalize $GIT_COMMIT
    """
    version = _getenv('GIT_COMMIT')
    cmd = ['sentry-cli', 'releases', 'finalize', version]
    return _run(cmd)


def release(*dirs):
    """Automates all the above ! VICTORY !"""
    if os.getenv('SENTRY_OVERWRITE', False):
        release_delete()
    release_new()
    release_set_commits()
    release_upload_js(*dirs)
    release_upload_sourcemaps(*dirs)
    release_finalize()
