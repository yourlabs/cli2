from cli2.file import File
from pathlib import Path
import importlib.metadata
import yaml


class Flow(File):
    PATH = '.cli2/flows'
    extension = 'yml'
    paths_ep = 'flow2_paths'
    plugins = dict()
    counter = 0
    package_path = Path(__file__).parent / 'flows'
    entry_point = 'flow2'

    def plugin_load(self, name):
        if not self.plugins:
            plugins = importlib.metadata.entry_points(
                group=self.entry_point,
            )
            for plugin in plugins:
                self.plugins[plugin.name] = plugin.load()

        if name not in self.plugins:
            raise Exception(f'{name} not registered plugin')
        return self.plugins[name]

    async def data_to_task(self, data):
        cls = self.plugin_load(data['plugin'])

        kwargs = data.copy()
        kwargs.pop('plugin')

        if 'name' not in kwargs:
            self.counter += 1
            args = [f'Task {self.counter}']
        else:
            args = [kwargs.pop('name')]

        if 'tasks' in kwargs:
            args += [
                await self.data_to_task(item)
                for item in kwargs.pop('tasks')
            ]
        tsk = cls(*args, **kwargs)

        return tsk

    async def run(self, **context):
        data = yaml.safe_load(self.content)
        task = await self.data_to_task(data)
        return await task.process(context)
