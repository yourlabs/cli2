"""
Ansible variables file reader with vault support

Why not use the Ansible Python API? We don't have a lot to do here, and the CLI
are less likely to be subject to changes.
"""

import cli2
import functools
import subprocess
import yaml
from pathlib import Path


class AnsibleVariablesError(Exception):
    pass


class PathNotFoundError(AnsibleVariablesError):
    pass


class UnresolvablePathError(AnsibleVariablesError):
    pass


class VaultPasswordFileRequiredError(AnsibleVariablesError):
    pass


class VaultPasswordFileNotFoundError(AnsibleVariablesError):
    pass


class Vault(yaml.YAMLObject):
    yaml_tag = '!vault'

    @classmethod
    def from_yaml(cls, loader, node):
        """
        Convert a representation node to a Python object.
        """
        return subprocess.check_output(
            f'echo \'{node.value}\''
            f' | {cls.ansible_vault}'
            f' decrypt --vault-password-file {cls.pass_path}',
            shell=True,
        ).decode().strip()


class Variables(dict):
    """
    Ansible variables reader.

    In general, it should be instanciated with :py:attr:`root_path` and
    :py:attr:`pass_path` to fully function correctly.

    Example:

    .. code-block:: python

        import cansible
        variables = cansible.Variables(
            root_path=Path(__file__).parent,
            pass_path='~/.vault_password',
        )
        print(variables['playbooks/vars/example.yml'])

    Every file read is cached in the variables object.

    .. py:attribute:: root_path

        Unless you feed this with only absolute path, you'll need a root_path
        so that relative paths can be resolved. This should be your collection
        root.

    .. py:attribute:: pass_path

        Unless you don't use ansible-vault, you'll need to give the pass to the
        vault password here.
    """
    def __init__(self, root_path=None, pass_path=None):
        self.root_path = Path(root_path) if root_path else None
        self.pass_path = Path(pass_path) if pass_path else None

    def __getitem__(self, key):
        if key not in self:
            self.read(key)
        return super().__getitem__(key)

    @functools.cached_property
    def ansible_vault(self):
        return cli2.which('ansible-vault')

    def read(self, path):
        """
        Read an ansible YAML variable file.

        :param path: Absolute path or path relative to :py:attr:`root_path`
        """
        key = path
        path = Path(path)

        if path.is_absolute():
            path = path
        elif self.root_path:
            path = self.root_path / path
        else:
            raise UnresolvablePathError(
                f'{path} must be absolute if root_path not set'
            )

        if not path.exists():
            raise PathNotFoundError(f'{path} does not exist')

        with path.open('r') as f:
            content = f.read()

        if content.strip().startswith('$ANSIBLE_VAULT'):
            if not self.pass_path:
                raise VaultPasswordFileRequiredError(
                    'Vault password required in pass_path'
                )
            if not self.pass_path.exists():
                raise VaultPasswordFileNotFoundError(
                    f'{self.pass_path} does not exist'
                )
            args = [
                self.ansible_vault,
                'view',
                '--vault-password-file',
                str(self.pass_path),
                str(path),
            ]
            content = subprocess.check_output(args)

        # todo: find a thread safe way to use our YAMLObject
        Vault.ansible_vault = self.ansible_vault
        Vault.pass_path = self.pass_path
        self[key] = yaml.load(content, Loader=yaml.FullLoader)
        return self[key]
