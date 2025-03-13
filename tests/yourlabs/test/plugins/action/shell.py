import copy
import cli2
import cansible
from ansible.plugins.action import display
from ansible.plugins.filter.core import to_nice_yaml


class ActionModule(cansible.ActionBase):
    cmd = cansible.Option('cmd')

    async def run_async(self):
        result = self.subprocess_remote(self.cmd)
        self.result['stdout'] = result['stdout']
        self.result['cmd'] = result['cmd']
        self.result['stdout_lines'] = result['stdout_lines']
