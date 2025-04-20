import cli2
import importlib.metadata
import jinja2
import functools
from flow2.task import Task


class TemplateTask(Task):
    pass


class Plugin:
    def __init__(self, name):
        self.name = name

    def paths(self):
        pass

    def macros(self):
        pass


class MacroFileSystemLoader(jinja2.FileSystemLoader):
    def __init__(self, macros, *args, **kwargs):
        self.macros = macros
        super().__init__(*args, **kwargs)

    def get_source(self, environment, template):
        source, filename, uptodate = super().get_source(environment, template)
        macros = macros_render(self.macros, template)
        modified_source = f"{macros}{source}"
        return modified_source, filename, uptodate


def macros_render(macros, template=None):
    if template:
        for path in macros.values():
            if path.endswith(template):
                # don't include macros in macros to avoid recursion
                return ''

    imports = []
    for namespace, path in macros.items():
        imports.append(
            ''.join([
                '{% import "',
                str(path),
                '" as ',
                namespace,
                ' %}',
            ])
        )
    return ''.join(imports)


class Template2:
    def __init__(self, plugins, paths=None, **options):
        self.plugins = plugins
        self.primary_paths = paths or []
        self.options = options or dict(
            undefined=jinja2.StrictUndefined,
            autoescape=False,
            enable_async=True,
        )

    @classmethod
    def factory(cls, paths=None, **options):
        plugins = {
            plugin.name: plugin.load()(plugin.name)
            for plugin in importlib.metadata.entry_points(group='template2')
        }
        return cls(plugins, paths=paths, **options)

    @functools.cached_property
    def macros(self):
        macros = dict()
        for name, plugin in self.plugins.items():
            if result := plugin.macros():
                macros.update(result)
        return macros

    @functools.cached_property
    def paths(self):
        paths = []
        paths += self.primary_paths
        for plugin in self.plugins.values():
            paths += plugin.paths() or []
        return paths

    @functools.cached_property
    def env(self):
        env = jinja2.Environment(
            loader=MacroFileSystemLoader(
                self.macros,
                [str(p) for p in self.paths],
            ),
            **self.options,
        )
        env.globals.update(self.plugins)
        return env

    async def render(self, content, **context):
        template = self.env.from_string(macros_render(self.macros) + content)
        cli2.log.debug('template', context=context, content=content)
        return await template.render_async(**context)


cli = cli2.Group()
cli.overrides['template2']['factory'] = lambda: Template2.factory()


@cli.cmd(color='green')
def plugins(template2):
    """
    List jinja2 plugins
    """
    return template2.plugins


@cli.cmd(color='green')
def macros(template2):
    """
    Show all Jinja2 macros, which you can call anywhere in your template.
    """
    return template2.macros


@cli.cmd(color='green')
def paths(template2):
    """
    Show all Jinja2 macros, which you can call anywhere in your template.
    """
    return [str(p) for p in template2.paths]


# shortcut function, for import template2; template2.render(...)
def render(content, paths=None, **context):
    return Template2.factory(paths=paths).render(content, **context)
