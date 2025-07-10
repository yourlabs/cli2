import cli2
import flow2


class FindPlugin(flow2.Task):
    def __init__(self, name, path='.', flags='', **kwargs):
        self.path = path
        self.flags = flags
        super().__init__(name, **kwargs)

    async def run(self, queue, context=None):
        return cli2.Find(self.path, flags=self.flags).run()
