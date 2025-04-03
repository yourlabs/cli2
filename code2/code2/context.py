import cli2
import functools


class Context:
    def __init__(self, project, path):
        self.path = path
        self.project = project

    @cli2.cmd
    def run(self, *command):
        """
        Run a command in the context, adding its output to the context.

        :param command: Command line to run
        """

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

    @cli2.cmd
    def show(self):
        """ Show the contents of the context """

    @cli2.cmd
    def dump(self):
        """ Dump context as given to LLM """

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
