import cli2
import copy
import cansible
from cclient.example import APIClient


class ActionModule(cansible.ActionBase):
    id = cansible.Option('id', default=None)
    name = cansible.Option('name')
    capacity = cansible.Option('capacity', default='1To')
    price = cansible.Option('price')
    state = cansible.Option('state', default='present')
    mask_keys = ['Price']

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
                self.result['deleted'] = obj.data
                await obj.delete()
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
            self.result['data'] = response.json()
            self.result['changed'] = True
            if self.verbosity:
                # causes a diff to be displayed
                self.after_set(obj.data)
        else:
            self.result['data'] = obj.data
            self.result['changed'] = False

    async def client_factory(self):
        return APIClient()
