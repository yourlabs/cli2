"""Document me !"""
import os
import subprocess


key_path = '.ssh_private_key'


def _setkeyfile():
    key = os.getenv('SSH_PRIVATE_KEY')
    if key:
        with open(key_path, 'w+') as f:
            f.write(key)
        os.chmod(key_path, 0o600)
        os.environ['GIT_SSH_COMMAND'] = ' '.join((
            f'ssh -i {key_path}',
            '-o StrictHostKeyChecking=no'
        ))


def _unsetkeyfile():
    if os.path.exists(key_path):
        os.unlink(key_path)


def _run(cmd):
    _setkeyfile()
    retcode = subprocess.run(['git'] + cmd).returncode
    _unsetkeyfile()
    return retcode


def clone(repo, dest=None):
    """Clone a repository

    This function helps you cloning a repository
    using you SSH_PRIVATE_KEY environment variable
    to authentify you

    :param repo: The repository which you want to clone
    :param dest: (optional) The directory where you want to clone to

    Examples::

        clitoo git.clone git@yourlabs.io:oss/clilabs.git
        clitoo git.clone git@yourlabs.io:oss/playlabs.git ~/yourlabs/playlabs
    """
    cmd = ['clone', repo]
    if dest:
        cmd.append(dest)
    return _run(cmd)


def apply():
    """Fetch - Stash - Apply routine.

    This function makes the following commands::

        git fetch origin
        git stash
        git reset --hard origin/master
        git stash apply

    The whole thing uses the SSH_PRIVATE_KEY environment variable
    for authentication if provided, helpful for CI executors, or executing in a
    container with a SSH key as env var.

    Example::

        $ clitoo git.apply
    """
    commands = [
        ['fetch', 'origin'],
        ['stash'],
        ['reset', '--hard', 'origin/master'],
        ['stash', 'apply']
    ]
    for cmd in commands:
        retcode = _run(cmd)
        if retcode:
            return retcode


def push(msg):
    """Add - Commit - Push routine

    This function makes the following commands::

        git commit -am commit_message
        git push

    Also supports $SSH_PRIVATE_KEY.

    :param message: Your commit message

    Example::

        clitoo git.push 'commit message'
    """
    commands = [
        ['commit', '-am', msg],
        ['push']
    ]
    for cmd in commands:
        retcode = _run(cmd)
        if retcode:
            return retcode
