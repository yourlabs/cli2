import cli2
import template2


class Cli2Template2Plugin(template2.Plugin):
    async def find(self, *args, **kwargs):
        return cli2.find(*args, **kwargs).run()

    async def files_read(self, paths, silent=True):
        return await cli2.files_read(paths, silent=silent)

    async def shell(self, *args, quiet=True):
        return (await cli2.Proc(*args, quiet=quiet).wait()).out
