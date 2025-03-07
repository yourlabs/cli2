import cli2
import chttpx


class APIClient(chttpx.Client):
    """
    Client for restful-api.dev

    Prior to using this, run at the root of this repository:

    .. code-block::

        pip install django djangorestframework
        ./manage.py migrate
        ./manage.py runserver
    """
    mask_keys = ['Capacity']

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('base_url', 'http://localhost:8000')
        super().__init__(*args, **kwargs)

    @cli2.cmd
    async def fail(self):
        """ Send bogus Form data """
        await self.post('/foo', data=dict(b=2))


class Object(APIClient.Model):
    """
    restful-api.dev objects

    Example:

    chttpx-example-client object create name=chttpx capacity=2TB
    """
    url_list = '/objects/'
    url_detail = '/objects/{self.id}/'

    id = chttpx.Field()
    name = chttpx.Field()
    capacity = chttpx.Field('data/Capacity')
    generation = chttpx.Field('data/Generation')
    price = chttpx.Field('data/Price')

    @cli2.cmd
    @classmethod
    async def fail(cls):
        """ Send bogus JSON """
        await cls.client.post('/foo', json=dict(a=1))

    @cli2.cmd
    async def rename(self, new_name):
        """ Send bogus JSON with an instance"""
        self.name = new_name
        return await self.save()

    async def update(self):
        return await self.client.put(self.url, json=self.data)


cli = APIClient.cli
