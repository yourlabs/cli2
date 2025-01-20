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
        target_name = f"cli2.{name}"
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

        longest = 0
        for name, command in self.command.items():
            if len(name) > longest:
                longest = len(name)

        rst = ['**SUB-COMMANDS**']
        for name, command in self.command.items():
            rst.append(f'\n:cli2:cmd:`~{self.command_name} {name}`')
            rst.append(command.doc_short)

        self.nodes += self.rst_nodes("\n".join(rst))
        return self.nodes


class Cli2Command(ObjectDescription):
    def synopsys(self):
        chain = [self.command_name]
        for name, arg in self.command.items():
            chain.append(synopsys_arg(arg))
        return "\n".join(chain)

    @functools.cached_property
    def description(self):
        rst = inspect.getdoc(self.command.target)
        if rst:
            doc = [
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
        self.nodes[1][0][0].children = self.rst_nodes(self.synopsys())
        if self.description:
            self.nodes[1].children += self.rst_nodes(self.description)
        self.nodes[1] += self.rst_nodes('**ARGUMENTS**')
        for name, argument in self.command.items():
            self.nodes[1].children += self.rst_nodes(
                f'    .. cli2:argument:: {self.command_name} {name}'
            )
        return self.nodes


class Cli2Argument(ObjectDescription):
    def run(self):
        self.nodes = super().run()

        self.nodes[1][0][0][0] = docutils.nodes.Text(
            synopsys_arg(self.argument)
        )

        fields = dict()
        if self.argument.doc:
            fields['description'] = self.argument.doc

        if len(self.argument.alias) > 1:
            fields['alias'] = ', '.join([
                f'``{x}``' for x in self.argument.alias
            ])

        if self.argument.negates:
            fields['negates'] = ', '.join([
                f'``{x}``' for x in self.argument.negates
            ])

        if self.argument.type:
            fields['type'] = self.argument.type.__name__

        if self.argument.default != inspect._empty:
            fields['default'] = self.argument.default

        if self.argument.type == bool and not self.argument.negates:
            fields['accepted'] = 'yes, 1, true, no, 0, false'

        if self.argument.param.kind == self.argument.param.VAR_KEYWORD:
            if self.argument.cmd.posix:
                ex = '--something=somevalue'
            else:
                ex = 'something=somevalue'
            fields['usage'] = f'Any number of named arguments, example: {ex}'

        elif self.argument.param.kind == self.argument.param.VAR_POSITIONAL:
            fields['usage'] = 'Any number of un-named arguments'

        self.nodes[1][0][0].children += self.rst_nodes("\n".join([
            f":{name}: {value}" for name, value in fields.items()
        ]))

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

    def run(self):
        section_node = docutils.nodes.section()
        section_node['ids'].append(docutils.nodes.make_id(self.command_name))

        # Add a title to the section
        title_node = docutils.nodes.title(text=f'{self.command_name}')
        section_node += title_node

        if isinstance(self.command, cli2.Group):
            section_node += self.rst_nodes(
                f'.. cli2:group:: {self.command_name}'
            )

        result = [section_node]

        groups = [self.command]
        while groups:
            group = groups.pop()
            for key, value in group.items():
                if key == 'help':
                    continue

                section_node = docutils.nodes.section()
                section_node['ids'].append(docutils.nodes.make_id(key))

                # Add a title to the section
                title_node = docutils.nodes.title(text=f'{value.path}')
                section_node += title_node

                if isinstance(value, cli2.Group):
                    section_node += self.rst_nodes(
                        f'.. cli2:group:: {value.path}'
                    )
                    groups.append(value)

                elif isinstance(value, cli2.Command):
                    section_node += self.rst_nodes(
                        f'.. cli2:command:: {value.path}'
                    )
                result.append(section_node)

        return result


class Cli2CommandRole(roles.XRefRole):
    def run(self):
        if self.target.startswith("~"):
            self.target = self.target[1:]
            self.text = self.target[1:]
            self.title = self.target.split(" ")[-1]
        return super().run()


class Cli2ArgumentRole(roles.XRefRole):
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
        grp=roles.XRefRole(),
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
        target_name = f"cli2.{target}"
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
