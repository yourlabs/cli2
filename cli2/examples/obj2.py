import cli2


class YourStuff:
    @classmethod
    @cli2.cmd
    def class_method(cls, arg):
        return cls, arg

    @cli2.cmd
    def instance_method(self, arg):
        return self, arg

    @cli2.cmd
    def noise(self):
        return 'noise'


class Child(YourStuff):
    noise = None


cli = cli2.Group()
cli.load(YourStuff)
cli.overrides['cls']['factory'] = lambda: YourStuff
cli.overrides['self']['factory'] = lambda: YourStuff()

nested = cli.group('child')
nested.load(Child)
nested.overrides['cls']['factory'] = lambda: Child
nested.overrides['self']['factory'] = lambda: Child()

if __name__ == '__main__':
    cli.entry_point()
