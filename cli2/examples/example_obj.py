#!/usr/bin/env python
import cli2


class ClientCommand(cli2.Command):
    def setargs(self):
        super().setargs()
        self.arg('base_url', kind='KEYWORD_ONLY', default='http://...')
        self['self'].factory = self.get_client

    def get_client(self):
        return Client(self['base_url'].value)


cli = cli2.Group(name="test", cmdclass=ClientCommand)


class Client:
    def __init__(self, base_url):
        self.base_url = base_url

    @cli.cmd
    def get(self, arg):
        return ('GET', self.base_url, arg)

    @cli.cmd
    def post(self, arg):
        return ('POST', self.base_url, arg)


if __name__ == '__main__':
    cli.entry_point()
