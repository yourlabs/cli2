import os
import re
import shlex
import shutil
import pty
import yaml

from clilabs import context
from processcontroller import ProcessController


def _find_config_file():
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f == 'clilabs-auto.yml' or \
               f == 'clilabs-auto.yaml':
                return os.path.join(root, f)


def _parse_file():
    file_path = _find_config_file()
    if not file_path:
        return None, None
    else:
        with open(file_path, 'r') as f:
            return file_path, yaml.load(f.read())


def _get_script(content, kwargs):
    if content and 'script' in content:
        script = content['script']
        if not script:
            return None
        for i, s in enumerate(script):
            for key, val in kwargs.items():
                script[i] = script[i].replace('${' + key + ':}', val)
            script[i] = re.sub('\$\{[^\${:}]*\:}', '', script[i])
            script[i] = shlex.split(script[i])
            script[i] = ' '.join(script[i])
        return script


def _get_shell_cmd():
    shells = ['bash -e', 'sh -e']
    if 'shell' in context.kwargs:
        shells.insert(0, context.kwargs['shell'])
    for shell in shells:
        if _run.shell_cmd is None:
            _run.shell_cmd = shlex.split(shell)
            _run.shell_cmd[0] = shutil.which(_run.shell_cmd[0])
            print(f'# Shell command {_run.shell_cmd}')
        return _run.shell_cmd


def _print_line(c, l):
    os.write(pty.STDOUT_FILENO, l.encode())


def _next_cmd(c, l):
    if _run.script_count is None:
        _run.script_count = 0
    _run.script_count += 1
    _run()


def _next_job(c, l):
    if _run.job_count is None:
        _run.job_count = 0
    _run.script_count = 0
    _run.job_count += 1
    _run()


def _abort(c, l):
    _run.script_count = len(_run.script)
    _run.exit_status = int(l.split(' ')[0])
    _run()


def _get_shell():
    if _run.shell is None:
        proc = ProcessController()
        proc.run(_get_shell_cmd(), {
            'detached': True,
            'private': True,
            'echo': False,
            'when': [
                ['^CLILABS_AUTO_JOB_COMPLETE_TOKEN$', _next_job],
                ['(?!^([0-9]* )?CLILABS_AUTO_.*_TOKEN$)', _print_line],
                ['^CLILABS_AUTO_DONE_TOKEN$', _next_cmd],
                ['^.*CLILABS_AUTO_ERR_TOKEN$', _abort],
            ]
        })
        _run.shell = proc
    return _run.shell


def _wait_shell():
    shell = _get_shell()
    pid, status = shell.wait()
    return _run.exit_status


def _run():
    shell = _get_shell()
    if _run.job_count < len(_run.jobs):
        _run.script = _run.jobs[_run.job_count][1]
        if _run.script_count < len(_run.script):
            instruction = _run.script[_run.script_count]
            print(instruction)
            shell.send('(' + instruction +
                       ' && echo CLILABS_AUTO_DONE_TOKEN )' +
                       ' || echo $? CLILABS_AUTO_ERR_TOKEN')
        else:
            if _run.exit_status is None:
                _run.exit_status = 0
            shell.send('echo CLILABS_AUTO_JOB_COMPLETE_TOKEN')
    else:
        shell.close()
    return shell.return_value


def _execute(jobs, kwargs):
    path, content = _parse_file()
    if not path:
        print('# Could not find any clilabs-auto configuration file')
        return 1
    print(f'# Using {path}')
    if not content and path:
        print('# No jobs found')
        return 2
    if not jobs:
        print('# Jobs found:')
        for j in content.keys():
            print(f'#\t{j}')
        return 0
    _run.shell_cmd = None
    cmd = _get_shell_cmd()
    _run.shell = None
    _get_shell()
    if not cmd or not len(cmd) or not cmd[0]:
        print(f'# Invalid shell command')
        return 5
    jobs_scripts = []
    for j in jobs.split(','):
        if j in content:
            print(f'# Running {j} job from {path}')
            script = (j, _get_script(content[j], kwargs))
            if not script[1]:
                print(f'# No script found for job {j}, ..aborting')
                return 4
            if _execute.debug:
                for i, s in enumerate(script[1]):
                    print(s)
            else:
                jobs_scripts.append(script)
        else:
            print(f'# Job {j} not found, ..aborting')
            return 3
    _run.job_count = 0
    _run.jobs = jobs_scripts
    _run.script_count = 0
    _run.script = None
    _run.exit_status = None
    _run()
    retcode = _wait_shell()
    print()
    if retcode:
        return retcode
    return 0


def play(jobs=None, **kwargs):
    """Play automation Jobs

    This function will walk in current tree, looking for a file called
    'clilabs-auto.yml' or 'clilabs-auto.yaml'.
    The walk will stop at the first matching file.

    It will then parse it looking for jobs matching with the first param

    If no job is specified, it will print the list of jobs found in the
    clilabs-auto config file

    :param jobs: a coma separated list of jobs
    :param **kwargs: a list of variables to dynamically assign to job vars

    The variables must be in the form ${name:} in the config file
    They will be replaced by the value of the kwarg name=value

    Variables are optional and will be replaced by an empty string if
    they are not specified in the command line without throwing any errors

    Examples:

    clilabs auto:play   # list jobs
    clilabs auto:play flake8    # play job flake8
    clilabs auto:play flake8,pytest pip_opt=--user  # play jobs flake8 and
                                                    # pytest setting var
                                                    # pip_opt to '--user'
    """
    _execute.debug = False
    return _execute(jobs, kwargs)


def debug(jobs=None, **kwargs):
    """Dry run of auto:play

    This function will only show what would have been done by the play function
    See play for more information:

    clilabs help auto:play
    """
    _execute.debug = True
    return _execute(jobs, kwargs)


main = debug
