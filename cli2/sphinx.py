import cli2
import docutils
import functools
import inspect
import textwrap

from sphinx import addnodes
from sphinx import domains
from sphinx import directives
from sphinx import roles
from sphinx.application import Sphinx
from sphinx.util import nodes
from sphinx.util import parsing
from sphinx.util.docutils import SphinxDirective


def synopsys_arg(arg):
    if arg.alias:
        out = '[' + arg.alias[-1]

        if arg.type != bool:
            out += '=' + arg.param.name.upper()

        if arg.negates:
            out += '|' + arg.negates[-1]
        out += ']'
        return out

    elif arg.param.kind == arg.param.VAR_POSITIONAL:
        return (
            '['
            + arg.param.name.upper()
            + ']...'
        )
    elif arg.param.kind == arg.param.VAR_KEYWORD:
        prefix = '--' if arg.cmd.posix else ''
        return (
            '['
            + prefix
            + arg.param.name.upper()
            + '='
            + 'VALUE'
            + ']...'
        )
    else:
        return arg.param.name.upper()


class Table(docutils.nodes.table):
    def __init__(self, headers):
        super().__init__()
        self['classes'] = ['align-left']
        self.tgroup = docutils.nodes.tgroup(cols=2)
        self.tgroup += docutils.nodes.colspec()
        self.tgroup += docutils.nodes.colspec()
        self += self.tgroup

        thead = docutils.nodes.thead()
        self.tgroup += thead

        header_row = docutils.nodes.row()
        for header in headers:
            cell = docutils.nodes.entry()
            cell += docutils.nodes.paragraph(text=header)
            header_row += cell

        thead += header_row

        self.tbody = docutils.nodes.tbody()
        self.tgroup += self.tbody

    def colspec(self, *args, **kwargs):
        self.tgroup += docutils.nodes.colspec(*args, **kwargs)

        self.header_row = docutils.nodes.row()
        for arg in args:
            self.colspec()

        for arg in args:
            cell = docutils.nodes.entry()
            cell += docutils.nodes.paragraph(text=arg)
            self.header_row += cell
        self.thead += self.header_row

    def row(self, *cells):
        row = docutils.nodes.row()
        for cell in cells:
            entry = docutils.nodes.entry()
            entry += cell
            row += entry
        self.tbody += row


class ObjectDescription(directives.ObjectDescription):
    def rst_nodes(self, rst):
        return parsing.nested_parse_to_nodes(
            self.state,
            textwrap.dedent(rst).strip(),
        )

    def run(self) -> list[nodes.Node]:
        self.nodes = super().run()
        return self.nodes

    @property
    def objects(self):
        return self.env.domaindata['cli2']['objects']

    def handle_signature(self, sig, signode):
        """
        Parse the object signature.
        - `sig`: The raw signature string.
        - `signode`: The node for rendering the signature.
        """
        name = sig.strip()
        signode += addnodes.desc_name(name, name)
        return name

    def add_target_and_index(self, name, sig, signode):
        """
        Define a cross-reference target and add it to the index.
        """
        target_name = f"cli2.{name.replace(' ', '-')}"
        if target_name not in self.objects:
            self.objects[target_name] = self.env.docname
            signode['ids'].append(target_name)

        self.indexnode['entries'].append(
            ('single', name, target_name, '', None)
        )


class Cli2Group(ObjectDescription):
    @functools.cached_property
    def command(self):
        return cli2.retrieve(self.command_name)

    @functools.cached_property
    def command_name(self):
        return self.arguments[0]

    def run(self) -> list[nodes.Node]:
        self.nodes = super().run()
        self.nodes[1][0][0].children = self.rst_nodes(
            f'``{self.command.path}``',
        )
        if self.command.doc:
            self.nodes[1][1] += self.rst_nodes(self.command.doc)

        longest = 0
        for name, command in self.command.items():
            if len(name) > longest:
                longest = len(name)

        table = Table(headers=('Sub-Command', 'Help'))
        for name, command in self.command.items():
            table.row(
                self.rst_nodes(f':cli2:cmd:`~{self.command_name} {name}`'),
                self.rst_nodes(command.doc_short),
            )

        self.nodes[1] += table
        return self.nodes


class Cli2Command(ObjectDescription):
    def synopsys(self):
        chain = [self.command_name]
        for name, arg in self.command.items():
            chain.append(synopsys_arg(arg))
        return " ".join(chain)

    @functools.cached_property
    def description(self):
        rst = inspect.getdoc(self.command.target)
        doc = []

        if self.command.target.__class__.__name__ == 'function':
            ref = '.'.join([
                self.command.target.__module__,
                self.command.target.__qualname__,
            ])
            doc.append(f'**Function**: :py:func:`{ref}`\n')

        if rst:
            doc += [
                line
                for line in rst.split("\n")
                if not line.startswith(':param')
            ]
        return "\n".join(doc).strip()

    @functools.cached_property
    def command(self):
        return cli2.retrieve(self.command_name)

    @functools.cached_property
    def command_name(self):
        return self.arguments[0]

    def run(self) -> list[nodes.Node]:
        self.nodes = super().run()
        self.nodes[1][0][0].children = self.rst_nodes(f'``{self.synopsys()}``')
        if self.description:
            self.nodes[1][1] += self.rst_nodes(self.description)

        if self.command.items():
            table = Table(headers=('Argument', 'Help'))

            for name, argument in self.command.items():
                table.row(
                    self.rst_nodes(f'``{synopsys_arg(argument)}``'),
                    self.rst_nodes(
                        f'.. cli2:argument:: {self.command_name} {name}',
                    ),
                )
            self.nodes[1][1] += table
        return self.nodes


class Cli2Argument(ObjectDescription):
    def run(self):
        super().run()

        node = docutils.nodes.container()
        node.attributes['ids'] = self.nodes[1][0].attributes['ids']

        self.nodes = [node]

        argument_doc = []

        if self.argument.doc:
            argument_doc += [self.argument.doc, '']

        def field(name, value):
            argument_doc.append(f'- **{name}**: {value}')

        field('Required', not self.argument.iskw)

        if len(self.argument.alias) > 1:
            field('Aliases', f'``{'``, ``'.join(self.argument.alias)}``')

        if self.argument.negates:
            field('Negates', f'``{'``, ``'.join(self.argument.negates)}``')

        if self.argument.type:
            field('Type', self.argument.type.__name__)

        if self.argument.default != inspect._empty:
            field('Default', self.argument.default)

        if self.argument.type == bool and not self.argument.negates:
            field('Accepted', 'yes, 1, true, no, 0, false')

        if self.argument.param.kind == self.argument.param.VAR_KEYWORD:
            if self.argument.cmd.posix:
                ex = '--something=somevalue --other=foo'
            else:
                ex = 'something=somevalue other=foo'
            field(
                'Usage',
                f'Any number of named self.arguments, ie.: ``{ex}``'
            )

        elif self.argument.param.kind == self.argument.param.VAR_POSITIONAL:
            if self.argument.cmd.posix:
                ex = '--something --other'
            else:
                ex = 'something other'
            field('usage', f'Any un-named arguments, ie.: ``{ex}``')

        self.nodes += self.rst_nodes('\n'.join(argument_doc))
        return self.nodes

    @functools.cached_property
    def argument_name(self):
        return self.arguments[0].split(" ")[-1]

    @functools.cached_property
    def command_name(self):
        return " ".join(self.arguments[0].split(" ")[:-1])

    @functools.cached_property
    def command(self):
        return cli2.retrieve(self.command_name)

    @functools.cached_property
    def argument(self):
        return self.command[self.argument_name]


class Cli2Auto(SphinxDirective):
    required_arguments = 1
    optional_arguments = 99

    @functools.cached_property
    def command_name(self):
        return " ".join(self.arguments)

    @functools.cached_property
    def command(self):
        return cli2.retrieve(self.command_name)

    def rst_nodes(self, rst):
        return parsing.nested_parse_to_nodes(
            self.state,
            textwrap.dedent(rst).strip(),
        )

    def _run(self, group=None):
        def section_node(name):
            section_node = docutils.nodes.section()
            section_node['ids'].append(docutils.nodes.make_id(name))
            title_node = docutils.nodes.title(text=name)
            section_node += title_node
            value = cli2.retrieve(name)
            if isinstance(value, cli2.Group):
                section_node += self.rst_nodes(
                    f'.. cli2:group:: {name}'
                )

            elif isinstance(value, cli2.Command):
                section_node += self.rst_nodes(
                    f'.. cli2:command:: {name}'
                )
            return section_node

        result = []
        result.append(section_node(group.path))

        group = group or self.command
        groups = []
        for key, value in group.items():
            if key == 'help':
                continue

            if isinstance(value, cli2.Group):
                groups.append(value)
            else:
                result[0] += section_node(value.path)

        for group in groups:
            result[0] += self._run(group)
        return result

    def run(self):
        return self._run(self.command)


class XRefRole(roles.XRefRole):
    def run(self):
        if self.target.startswith("~"):
            self.target = self.target[1:]
            self.text = self.text[1:]
            self.title = self.title.split(" ")[-1]

        # Apparently Sphinx doesn't like spaces in ids very much
        self.target = self.target.replace(' ', '-')

        return super().run()


class Cli2CommandRole(XRefRole):
    pass


class Cli2ArgumentRole(XRefRole):
    @functools.cached_property
    def command_name(self):
        return " ".join(self.target.split(" ")[:-1])

    @functools.cached_property
    def command(self):
        return cli2.retrieve(self.command_name)

    @functools.cached_property
    def argument_name(self):
        return self.target.split(" ")[-1]

    @functools.cached_property
    def argument(self):
        return self.command[self.argument_name]

    def run(self):
        if self.command.posix:
            self.title = f'--{self.argument_name.replace("_", "-")}'
            self.text = self.title
        return super().run()


class Cli2Domain(domains.Domain):
    """
    Sphinx Domain for cli2 stuff
    """
    name = 'cli2'
    label = 'cli2'
    object_types = dict(
        group=domains.ObjType('group', 'grp'),
        command=domains.ObjType('command', 'cmd'),
        argument=domains.ObjType('argument', 'arg'),
    )
    directives = dict(
        auto=Cli2Auto,
        group=Cli2Group,
        command=Cli2Command,
        argument=Cli2Argument,
    )
    roles = dict(
        grp=XRefRole(),
        cmd=Cli2CommandRole(),
        arg=Cli2ArgumentRole(),
    )
    initial_data = dict(
        # Stores all objects in this domain
        objects=dict(),
    )

    def resolve_xref(self, env, fromdocname, builder, typ, target, node,
                     contnode):
        """
        Resolve a cross-reference.
        """
        target_name = f"cli2.{target.replace(' ', '-')}"
        if target_name in self.data['objects']:
            return nodes.make_refnode(
                builder, fromdocname, self.data['objects'][target_name],
                target_name, contnode, target
            )


def setup(app: Sphinx):
    app.add_domain(Cli2Domain)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
