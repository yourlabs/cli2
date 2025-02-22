import cli2
import copy
from cli2 import ansible
from cli2.examples.client import APIClient


class ActionModule(ansible.ActionBase):
    id = ansible.Option('id', default=None)
    name = ansible.Option('name')
    capacity = ansible.Option('capacity', default='1To')
    price = ansible.Option('price')
    state = ansible.Option('state', default='present')

    async def run_async(self):
        self.log = cli2.log.bind(id=self.id, name=self.name)
        obj = None

        if self.id:
            obj = await self.client.Object.get(id=self.id)
        elif self.name:
            obj = await self.client.Object.find(name=self.name).first()

        if obj:
            self.log.info(f'Found object')

        if self.state == 'absent':
            if obj:
                response = await obj.delete()
                # this returns masked json or content in value
                # key will be "json" or "content"
                key, value = self.client.response_log_data(response)
                self.result[key] = value
                self.result['changed'] = True
                self.log.info(f'Deleted object')
            return

        if obj is not None:
            if self.verbosity:
                # will cause a diff to display
                self.before_set(obj.data)
        else:
            obj = self.client.Object()

        obj.name = self.name
        obj.capacity = self.capacity
        obj.price = self.price

        if obj.changed_fields:
            response = await obj.save()
            self.log.info(f'Object changes saved')
            key, value = self.client.response_log_data(response)
            self.result[key] = value
            self.result['changed'] = True
            if self.verbosity:
                # causes a diff to be displayed
                self.after_set(obj.data)
        else:
            self.result['json'] = obj.data_masked
            self.result['changed'] = False

    async def client_factory(self):
        return APIClient()
