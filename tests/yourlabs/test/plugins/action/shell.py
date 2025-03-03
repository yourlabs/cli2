import copy
import cli2
from cli2 import ansible
from ansible.plugins.action import display
from ansible.plugins.filter.core import to_nice_yaml


import madbg
class ActionModule(ansible.ActionBase):
    cmd = ansible.Option('cmd')
    mask = ansible.Option(fact='mask')

    async def run_async(self):
        self.result['cmd'] = self.subprocess_remote(self.cmd)

    '''
    def subprocess_remote(self, cmd, **kwargs):
        new_task = self._task.copy()
        new_task.args = dict(_raw_params=cmd, **kwargs)
        display.display(
            f'<{self.task_vars["inventory_hostname"]}> + '
            + self.mask_data(cmd),
            color='blue',
        )
        shell_action = self._shared_loader_obj.action_loader.get(
            'ansible.builtin.shell',
            task=new_task,
            connection=self._connection,
            play_context=self._play_context,
            loader=self._loader,
            templar=self._templar,
            shared_loader_obj=self._shared_loader_obj,
        )
        result = shell_action.run(task_vars=self.task_vars.copy())

        if 'stderr_lines' in result:
            print(self.mask_data(result['stderr']))
        if 'stdout_lines' in result:
            print(self.mask_data(result['stdout']))

        result.pop('invocation')
        return self.mask_data(copy.deepcopy(result))
    '''
