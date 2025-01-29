import cli2

cli = cli2.Group('cli2-example-client')


class APIClient(cli2.Client):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('base_url', 'https://api.restful-api.dev/')
        super().__init__(*args, **kwargs)


cli.cmd(APIClient.get, doc='Try get /')


class Object(APIClient.model):
    url_list = '/objects'
    url_detail = '/objects/{self.url_id}'

    @classmethod
    @cli.cmd
    async def fail(cls):
        await cls.client.post('/foo', json=[1])


cli.cmd(Object.find)
