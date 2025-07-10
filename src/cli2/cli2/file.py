from cli2.display import highlight
from cli2.interactive import editor
from cli2.theme import t
from cli2.cli import cmd, Command, Cli2ValueError
from cli2.exceptions import NotFoundError
from cli2.log import log
import os
import importlib.metadata
from pathlib import Path


ep_paths_cache = dict()


class FileType(type):
    PATH = '.cli2/file'

    @property
    def user_path(cls):
        env_name = getattr(cls, 'USER_PATH_ENV', None)
        if not env_name:
            env_name = f'{cls.__name__.upper()}_USER_PATH'

        if env_name in os.environ:
            return Path(os.getenv(env_name))
        else:
            return Path(os.getenv('HOME')) / cls.PATH

    @property
    def local_path(cls):
        env_name = getattr(cls, 'LOCAL_PATH_ENV', None)
        if not env_name:
            env_name = f'{cls.__name__.upper()}_LOCAL_PATH'

        if env_name in os.environ:
            return Path(os.getenv(env_name))
        else:
            return Path(os.getcwd()) / cls.PATH


class File(metaclass=FileType):
    paths_ep = None
    extension = 'txt'
    package_path = None

    class NotFoundError(NotFoundError):
        pass

    def __init__(self, path=None, content=None):
        self.path = path
        self.content = content

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        try:
            path = Path(value)
        except:  # noqa
            pass
        else:
            if not path.is_file():
                path = self.find(value)
            self._path = path

    @property
    def name(self):
        return self.path.name[:4]

    @property
    def content(self):
        if not self._content:
            with self.path.open('r') as f:
                self._content = f.read()
            log.debug(
                'file loaded',
                path=str(self.path),
                content=self._content,
            )
        return self._content

    @content.setter
    def content(self, value):
        self._content = self.content_load(value)

    def content_load(self, content):
        return content

    @classmethod
    def paths(cls):
        paths = []

        if cls.local_path:
            paths.append(cls.local_path)

        if cls.user_path != cls.local_path:
            # don't append when in home
            paths.append(cls.user_path)

        if cls.paths_ep and not ep_paths_cache.get(cls):
            plugins = importlib.metadata.entry_points(
                group=cls.paths_ep,
            )
            if cls not in ep_paths_cache:
                ep_paths_cache[cls] = []
            for plugin in plugins:
                ep_paths_cache[cls] += plugin.load()()

        if cls in ep_paths_cache:
            paths += ep_paths_cache[cls]

        if cls.package_path:
            # add package provided ones
            paths.append(cls.package_path)
        return paths

    @classmethod
    def find(cls, name, paths=None):
        paths = paths or cls.paths()
        for path in paths:
            path = path / f'{name}.{cls.extension}'
            if path.exists():
                return path
        raise cls.NotFoundError(name, paths)

    async def render(self):
        return self.content


class FileCommand(Command):
    file_cls = File
    file_arg = 'file'

    def file_parse(self):
        if self.file_arg in self:
            try:
                context = self['context'].value
            except (Cli2ValueError, KeyError):
                context = dict()

            self[self.file_arg].value = self.file_cls(
                self[self.file_arg].value,
                **context,
            )

    def parse(self, *argv):
        error = super().parse(*argv)
        if error:
            return error
        self.file_parse()


class FileCommands:
    def __init__(self, cls=None, lexer=None, default_content=None):
        self.cls = cls or File
        self.lexer = lexer
        self.default_content = default_content or ''

    @cmd(color='gray')
    def paths(self):
        """
        Return file paths
        """
        return [str(p) for p in self.cls.paths()]

    @cmd(color='green')
    def list(self):
        """
        List available files
        """
        paths = dict()
        for path in self.cls.paths():
            if not path.exists():
                continue
            paths.update({
                p.name[:-4]: str(p)
                for p in path.iterdir()
                if p.name.endswith(f'.{self.cls.extension}')
            })
        return paths

    @cmd(cls=FileCommand)
    def edit(self, name, local: bool = False):
        """
        Edit a file.

        :param name: file name.
        :param local: Enable this to store in $CWD/.file2 instead of
                      $HOME/.file2
        """
        try:
            file = self.cls(name)
        except self.cls.NotFoundError:
            if local:
                path = self.cls.local_path
            else:
                path = self.cls.user_path
            path = path / f'{name}.{self.cls.extension}'
            kwargs = dict(content=self.default_content, path=path)
        else:
            path = file.path
            kwargs = dict(path=file.path)

        editor(**kwargs)
        print(t.bold('SAVED file: ') + t.green(f'{path}'))

    @cmd(color='green', cls=FileCommand)
    def show(self, file, _cli2=None):
        """
        Show a file

        :param file: file name
        """
        print(t.y.bold('PATH'))
        print(t.orange(file.path))
        print()

        print(t.y.bold('CONTENT'))
        print(self.highlight(file.content))

    @cmd(cls=FileCommand)
    async def render(self, file, **context):
        """
        Render a file with a given template context.

        :param file: file name
        :param context: Context variables.
        """
        print(t.y.bold('PATH'))
        print(t.orange(file.path))
        print()

        print(t.y.bold('OUTPUT'))
        print(self.highlight(await file.render()))

    def highlight(self, content):
        if self.lexer:
            return highlight(content, self.lexer)
        return content
