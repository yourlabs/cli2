import cli2

cli = cli2.Group('cli2-example-client')


@cli2.factories
class GitHubClient(cli2.Client):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('base_url', 'https://api.github.com/')
        kwargs.setdefault('headers', {})
        kwargs['headers'].setdefault('Accept', 'application/vnd.github+json')
        kwargs['headers'].setdefault('X-GitHub-Api-Version', '2022-11-28')
        super().__init__(*args, **kwargs)


cli.cmd(GitHubClient.get, doc='Try get /events')


@GitHubClient.model
class GitHubEvent(dict):
    @classmethod
    @cli.cmd
    async def find(cls, **params):
        return cls.client.paginate('events', params, cls)
