import cli2
import functools
import yaml


class Context:
    def __init__(self, project, path):
        self.path = path
        self.project = project
        self._data = dict()

    @property
    def data(self):
        if not self._data and self.data_path.exists():
            self._data = self.yaml_load('data')
        return self._data

    def data_save(self):
        self.yaml_save('data', self.data)

    @functools.cached_property
    def data_path(self):
        return self.path / 'data.yml'

    @property
    def name(self):
        return self.path.name

    @property
    def archived(self):
        return (self.path / 'archived').exists()

    @cli2.cmd
    def files(self, *paths, remove: bool=False):
        """
        Manage files in the context.

        Without argument, this dumps the files in the context.
        With paths as argument, it will add the files to the context.
        Unless "remove" is specified.

        :param paths: Paths of the files to add.
        :param remove: Wether to remove given paths.
        """
        files = self.yaml_load('files', [])

        if paths:
            paths = [str(path) for path in paths]

            project_files = self.project.files()

            # convert path list into a fixed path list and drop any path that's
            # not already in the context
            paths = [
                cli2.closest_path(path, project_files)
                if path not in project_files
                else path
                for path in paths
            ]
            # now ensure we don't duplicate (why not use a set?)
            paths = [path for path in paths if path not in files]

            if paths:
                # user can add them all at once or one by one
                if cli2.choice(f'Add {", ".join([str(p) for p in paths])} to context?') == 'y':
                    add = paths
                else:
                    add = []
                    for path in paths:
                        if cli2.choice(f'Add {path} to context?') == 'y':
                            add.append(path)

                for file in add:
                    files.append(str(file))
                self.yaml_save('files', files)
        return files

    def yaml_load(self, key, default=None):
        path = self.path / f'{key}.yml'
        if not path.exists():
            return default

        with path.open('r') as f:
            return yaml.safe_load(f.read())

    def yaml_save(self, key, data):
        self.path.mkdir(exist_ok=True, parents=True)
        path = self.path / f'{key}.yml'
        with path.open('w') as f:
            f.write(yaml.dump(data))

    @functools.cached_property
    def history_path(self):
        return self.path / 'history'

    def save(self, key, data):
        self.history_path.mkdir(exist_ok=True, parents=True)

        with (self.history_path / key).open('w') as f:
            f.write(data)

    def load(self, key):
        path = self.history_path / key

        if not path.exists():
            return None

        with path.open('r') as f:
            return f.read()
