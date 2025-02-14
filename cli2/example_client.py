import cli2


class APIClient(cli2.Client):
    """
    Client for restful-api.dev
    """
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('base_url', 'https://api.restful-api.dev/')
        super().__init__(*args, **kwargs)


class Object(APIClient.Model):
    """
    restful-api.dev objects
    """
    url_list = '/objects'
    url_detail = '/objects/{self.id}'

    id = cli2.Field()

    @cli2.cmd
    @classmethod
    async def fail(cls):
        """ Send bogus JSON """
        await cls.client.post('/foo', json=dict(a=1))

    @classmethod
    @cli2.cmd
    async def fail2(cls):
        """ Send bogus Form data """
        await cls.client.post('/foo', data=dict(b=2))


cli = APIClient.cli
