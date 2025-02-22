#!/usr/bin/env python
import cli2


class ClientCommand(cli2.Command):
    def setargs(self):
        super().setargs()
        if 'self' in self:
            self.arg(
                'base_url',
                kind='KEYWORD_ONLY',
                default='http://example.com',
            )
            self['self'].factory = self.get_client

    def get_client(self):
        return Client(self['base_url'].value)


cli = cli2.Group(cmdclass=ClientCommand, doc="blabla")


class Client:
    """Hello"""
    def __init__(self, base_url):
        self.base_url = base_url

    @cli.cmd
    def get(self, arg):
        """
        Run GET request

        Exmple link to :py:class:`~cli2.command.Command`:

        .. code:: yaml

            test:
              foo:
              - bar

        :param arg: Some argument
        """
        return ('GET', self.base_url, arg)

    @cli.cmd
    def post(self, arg):
        return ('POST', self.base_url, arg)

    @cli.cmd
    @cli2.arg('foo', alias=['foo', 'f', 'foooo'])
    def yourcmd(self, somearg: int, x=None, verbose: bool = False, *args,
                foo: str = None, **kwargs):
        """
        Test command

        :param somearg: Some arg documentation
        :param verbose: Enable verbose mode
        """
        pass


@cli.cmd
def noarg():
    """ oo """


@cli.cmd
def nodoc():
    pass


nested = cli.group("nested", doc="Nested group")
nested = nested.group("nested", doc="Nested group 2")
nested = nested.group("nested", doc="Nested group 3")
