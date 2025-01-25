import cli2
import os

cli = cli2.Group('cli2-example-client')


@cli2.factories(self='factory')
class GitHubClient(cli2.Client):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('base_url', 'https://api.github.com/')
        kwargs.setdefault('headers', {})
        kwargs['headers'].setdefault('Accept', 'application/vnd.github+json')
        kwargs['headers'].setdefault('X-GitHub-Api-Version', '2022-11-28')
        super().__init__(*args, **kwargs)

    @classmethod
    async def factory(cls):
        return cls(headers={'Authorization': 'Bearer ' + os.getenv('TOKEN')})


cli.cmd(GitHubClient.get, doc='Try get /events')


@GitHubClient.model
class GitHubEvent(cli2.Model):
    @classmethod
    @cli.cmd
    async def find(cls, **params):
        return cls.client.paginate('events', params, cls)

    @classmethod
    @cli.cmd
    async def search(cls, **params):
        async for event in cls.client.paginate('events', params, cls):
            yield event['id']

    @classmethod
    @cli.cmd
    async def create(cls, **params):
        return cls.client.post('events', json=params)
