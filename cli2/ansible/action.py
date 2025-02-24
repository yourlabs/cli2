"""
Experimental: my base class for Ansible actions.
"""

import asyncio
import cli2
import copy
import os
import re
import traceback

from ansible.plugins.action import ActionBase

# colors:
# black
# bright gray
# blue
# white
# green
# cyan
# bright green
# red
# bright cyan
# purple
# bright red
# yellow
# bright purple
# dark gray
# magenta
# bright magenta
# normal

# 7-bit C1 ANSI sequences
ansi_escape = re.compile(r'''
    \x1B  # ESC
    (?:   # 7-bit C1 Fe (except CSI)
        [@-Z\\-_]
    |     # or [ for CSI, followed by a control sequence
        \[
        [0-?]*  # Parameter bytes
        [ -/]*  # Intermediate bytes
        [@-~]   # Final byte
    )
''', re.VERBOSE)


UNSET_DEFAULT = '__UNSET__DEFAULT__'


class Option:
    """
    Ansible Option descriptor.

    .. py:attribute:: arg

        Name of the task argument to get this option value from

    .. py:attribute:: fact

        Name of the fact, if any, to get a value for this option if no task arg
        is provided

    .. py:attribute:: default

        Default value, if any, in case neither of arg and fact were defined.
    """
    UNSET_DEFAULT = UNSET_DEFAULT

    def __init__(self, arg=None, fact=None, default=UNSET_DEFAULT):
        self.arg = arg
        self.fact = fact
        self.default = default

    @property
    def kwargs(self):
        kwargs = dict(default=self.default)
        if self.arg:
            kwargs['arg_name'] = self.arg
        if self.fact:
            kwargs['fact_name'] = self.fact
        return kwargs

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        try:
            return obj.get(**self.kwargs)
        except AttributeError:
            raise AnsibleOptionError(self)


class AnsibleError(Exception):
    pass


class AnsibleOptionError(AnsibleError):
    def __init__(self, option):
        self.option = option
        super().__init__(option.kwargs)

    @property
    def message(self):
        message = ['Missing']
        if self.option.arg:
            message.append(f'arg `{self.option.arg}`')
            if self.option.fact:
                message.append('or')
        if self.option.fact:
            message.append(f'fact `{self.option.fact}`')
        return ' '.join(message)


class ActionBase(ActionBase):
    """
    Base action class

    .. py:attribute:: result

        Result dict that will be returned to Ansible

    .. py:attribute:: task_vars

        The task_vars that the module was called with

    .. py:attribute:: client

        The client object generated by :py:meth:`client_factory` if you
        implement it.
    """
    def get(self, arg_name=None, fact_name=None, default=UNSET_DEFAULT):
        if arg_name and arg_name in self._task.args:
            return self._task.args[arg_name]
        if fact_name and fact_name in self.task_vars:
            return self.task_vars[fact_name]
        if default != UNSET_DEFAULT:
            return default
        if fact_name:
            raise AttributeError(f'Undefined {arg_name} or {fact_name}')
        else:
            raise AttributeError(f'Undefined arg {arg_name}')

    def run(self, tmp=None, task_vars=None):
        self.tmp = tmp
        self.task_vars = task_vars
        self.result = super().run(tmp, task_vars)
        asyncio.run(self.run_wrapped_async())
        return self.result

    async def run_wrapped_async(self):
        self.verbosity = self.task_vars.get('ansible_verbosity', 0)

        if 'LOG_LEVEL' not in os.environ and 'DEBUG' not in os.environ:
            if self.verbosity == 1:
                os.environ['LOG_LEVEL'] = 'INFO'
            elif self.verbosity >= 2:
                os.environ['LOG_LEVEL'] = 'DEBUG'
            cli2.configure()

        try:
            try:
                self.client = await self.client_factory()
            except NotImplementedError:
                self.client = None
            await self.run_async()
        except Exception as exc:
            self.result['failed'] = True

            if isinstance(exc, AnsibleError):
                self.result['error'] = exc.message
            elif isinstance(exc, cli2.ResponseError):
                self.result.update(dict(
                    method=exc.method,
                    url=exc.url,
                    status_code=exc.status_code,
                ))
                key, value = self.client.response_log_data(exc.response)
                if key:
                    self.result[f'response_{key}'] = value
                key, value = self.client.request_log_data(exc.request)
                if key:
                    self.result[f'request_{key}'] = value
            elif self.verbosity:
                traceback.print_exc()

            # for pytest to raise
            self.exc = exc
        finally:
            if (
                self._before_data != UNSET_DEFAULT
                and self._after_data != UNSET_DEFAULT
            ):
                diff = cli2.diff_data(
                    self._before_data,
                    self._after_data,
                    self._before_label,
                    self._after_label,
                )
                if self.client and self.client.mask:
                    output = '\n'.join([
                        line.rstrip() for line in diff if line.strip()
                    ])
                    output = re.sub(
                        f'({"|".join(self.client.mask)}): (.*)',
                        '\\1: ***MASKED***',
                        ''.join(output),
                    )
                    print(cli2.highlight(output, 'Diff'))
                else:
                    cli2.diff(diff)

    async def run_async(self):
        """
        The method you are supposed to implement.

        It should:

        - provision the :py:attr:`result` dict
        - find task_vars in :py:attr:`task_vars`
        """

    async def client_factory(self):
        """
        Return a client instance.

        :raise NotImplementedError: By default
        """
        raise NotImplementedError()

    @classmethod
    async def run_test_async(cls, args=None, facts=None, client=None,
                             fail=False):
        """
        Test run the module in a mocked context.

        :param args: Dict of task arguments
        :param facts: Dict of play facts
        :param client: Client instance, overrides the factory
        :param fail: Allow this test to fail without exception
        """
        from unittest import mock
        obj = cls(*[mock.Mock()] * 6)
        obj.tmp = None
        obj.result = dict()
        obj._task = mock.Mock()
        obj._task.args = args or {}
        obj.task_vars = facts or {}
        obj.task_vars.setdefault('ansible_verbosity', 2)
        obj.exc = False
        if client:
            async def _factory():
                return client
            obj.client_factory = _factory
        old = obj.client_factory

        async def set_tries():
            client = await old()
            client.handler.tries = 0
            return client
        obj.client_factory = set_tries
        await obj.run_wrapped_async()
        if obj.exc and not fail:
            raise obj.exc
        if obj.result.get('failed', False) and not fail:
            raise Exception('Module failed, and fail is not True {obj.result}')
        return obj

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._before_data = UNSET_DEFAULT
        self._after_data = UNSET_DEFAULT

    def before_set(self, data, label='before'):
        """
        Set the data we're going to display the diff for at the end.

        :param data: Dictionnary of data
        :param label: Label to show in diff
        """
        self._before_data = copy.deepcopy(data)
        self._before_label = label

    def after_set(self, data, label='after'):
        """
        Set the data we're going to display the diff for at the end.

        :param data: Dictionnary of data
        :param label: Label to show in diff
        """
        self._after_data = copy.deepcopy(data)
        self._after_label = label
