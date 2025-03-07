import copy
import os
import re
import shlex
import shutil
import subprocess
import sys
import yaml

from cansible import ansi_escape


def which_ansible_playbook():
    PATH = os.environ.get('PATH', os.defpath)
    local = os.path.join(os.environ.get('HOME', '~'), '.local/bin')
    if local not in PATH:
        PATH = ':'.join([local, PATH])
    path = shutil.which('ansible-playbook', path=PATH)
    if not path:
        raise Exception('No ansible-playbook command in $PATH=' + PATH)
    return path


def check_ansible_output_for_exception(exception):
    # if you read this, it means a Python exception was throw during Ansible
    # execution, this must not happen for tests to pass
    assert not exception, 'Exception detected in ansible output'


def ansible_playbook(*args):
    cmd = [
        which_ansible_playbook(),
        '-c',
        'local',
        '-vvv',
        '--become',
        *args,
    ]

    try:
        readable = {shlex.join(cmd)}
    except AttributeError:  # old python
        readable = ' '.join([shlex.quote(arg) for arg in cmd])
    print(f'Running:\n{readable}')

    data = dict(
        ok=0,
        changed=0,
        unreachable=0,
        failed=0,
        skipped=0,
        rescued=0,
        ignored=0,
        exception=False,
    )

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    lines = []
    for line in iter(proc.stdout.readline, b''):
        line = line.decode()
        if 'Traceback (most recent call last)' in line:
            data['exception'] = True
        sys.stdout.write(line)
        if not line.strip():
            continue
        lines.append(ansi_escape.sub('', line))

    for line in reversed(lines):
        if line.startswith('PLAY RECAP'):
            break
        try:
            for item in re.findall('([a-z]+)=([0-9]*)', line):
                data[item[0]] += int(item[1])
        except (IndexError, KeyError):
            return dict(success=False)

    data['stdout'] = '\n'.join(lines)

    data['success'] = (
        data['ok']
        and not (data['failed'] or data['unreachable'])
    )
    return data


class Playbook:
    """
    On-the-fly playbook generator

    .. py:attribute:: root

        This would be a tmp_path returned by pytest

    .. py:attribute:: name

        Name of the playbook, test name by default

    .. py:attribute:: vars

        Playbook vars

    .. py:attribute:: roles

        Playbook roles, use :py:meth:`role_add` to add a role

    .. py:attribute:: tasks

        Playbook tasks, use :py:meth:`task_add` to add a task

    .. py:attribute:: play

        Main playbook play

    .. py:attribute:: plays

        Playbook plays, contains the main one by default

    .. py:attribute:: yaml

        Property that returns the generated yaml
    """

    def __init__(self, root, name):
        self.root = root
        self.name = name
        self.vars = dict()
        self.roles = []
        self.tasks = []
        self.play = dict(
            hosts='localhost',
            vars=self.vars,
            roles=self.roles,
            tasks=self.tasks,
        )
        self.plays = [self.play]

    def role_add(self, name, *tasks, **variables):
        """
        Create a new role with given tasks, include it with given variables

        :param name: role name
        :param tasks: List of task dicts
        :param variables: Variables that will be passed to include_role
        """
        self.roles.append(dict(
            role=str(self.root / name),
            tasks=tasks,
            **variables,
        ))

    def task_add(self, module, args=None, **kwargs):
        """
        Add a module call

        :param module: Name of the Ansible module
        :param args: Ansible module args
        :param kwargs: Task kwargs (register, etc)
        """
        task = {module: args if args else None}
        task.update(kwargs)
        self.tasks.append(task)

    @property
    def file_path(self):
        return self.root / f'{self.name}.yml'

    def yaml_dump(self, value):
        try:
            return yaml.dump(value, width=1000, sort_keys=False)
        except TypeError:  # python36
            return yaml.dump(value, width=1000)

    @property
    def yaml(self):
        plays = copy.deepcopy(self.plays)
        for play in plays:
            for role in play.get('roles', []):
                if 'tasks' not in role:
                    # actual role to include
                    continue
                # create role on the fly
                tasks = role.pop('tasks')
                role_path = self.root / role['role']
                tasks_path = role_path / 'tasks'
                if not tasks_path.exists():
                    tasks_path.mkdir(parents=True)
                with (tasks_path / 'main.yml').open('w+') as f:
                    f.write(self.yaml_dump(list(tasks)))
        return self.yaml_dump(plays)

    def write(self):
        with open(self.file_path, 'w+') as f:
            f.write(self.yaml)

    def __call__(self, *args, fails=False, exception=False):
        """
        Actually execute the playbook

        :param args: Any extra ansible args
        :param fails: Playbook failure is not accepted by default, set this to
                      True to allow a playbook to fail.
        :param exception: Exception during playbook run is not accepted by
                          default, set this to True to allow an exception to
                          pop in the playbook.
        """
        os.environ['ANSIBLE_STDOUT_CALLBACK'] = 'yaml'
        os.environ['ANSIBLE_FORCE_COLOR'] = '1'
        if not self.file_path.exists():
            self.write()
        result = ansible_playbook(*list(args) + [str(self.file_path)])
        assert result['success'] if not fails else not result['success']
        if not exception:
            check_ansible_output_for_exception(result['exception'])
        return result
