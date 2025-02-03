import cli2


class APIClient(cli2.Client):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('base_url', 'https://api.restful-api.dev/')
        super().__init__(*args, **kwargs)


class Object(APIClient.Model):
    url_list = '/objects'
    url_detail = '/objects/{self.id}'

    id = cli2.Field()

    @classmethod
    @APIClient.cli.cmd
    async def fail(cls):
        await cls.client.post('/foo', json=[1])


cli = APIClient.cli
