"""
12-factor interactive self-building lazy configuration.

The developer story we are after:

- there's nothing to do, just expect ``cli2.cfg['YOUR_ENV_VAR']`` to work one
  way or another
- when there's a minute to be nice to the user, add some help that will be
  displayed to them: ``cli2.cfg.questions['YOUR_ENV_VAR'] = 'this is a help
  text that will be display to the user when we prompt them for YOUR_ENV_VAR'``

This is the user story we are after:

- user runs your cli2 command right after install without any configuration
- the user is prompted for a variable
- the variable is saved in their ~/.profile in a new export line
- the user runs a command again in the same shell: we should find the variable
  in ~/.profile so he doesn't have to start a new shell for his new
  configuration to work

Of course, if the environment variable is already present in the environment
then this basically returns it from ``os.environ``.
"""

import functools
import os
import re
import shlex
import textwrap
from pathlib import Path


class Configuration(dict):
    """
    Configuration object.

    Wraps around environment variable and can question the user for missing
    variables and save them in his shell profile.

    .. py:attribute:: questions

        A dict of ``ENV_VAR=question_string``, if an env var is missing from
        configuration then question_string will be used as text to prompt the
        user.

    .. py:attribute:: profile_path

        Path to the shell profile to save/read variables, defaults to
        ~/.profile which should work in many shells.

    You can also just work with the module level ("singleton") instance, have
    scripts like:

    .. code-block:: python

        import cli2

        cli = cli2.Group()

        cli2.cfg['API_URL'] = 'What is your API URL?'

        @cli.cmd
        def foo():
            api_url = cli2.cfg['API_URL']

            # when there's no question, it'll use the var name as prompt
            api_url = cli2.cfg['USERNAME']

    """
    def __init__(self, profile_path=None, **questions):
        self.questions = questions
        self.profile_path = Path(
            profile_path or os.getenv('HOME') + '/.profile'
        )
        self._profile_script = None
        self._profile_variables = dict()
        self.environ = os.environ.copy()

    def input(self, prompt):
        """
        Wraps around Python's input but adds confirmation.

        :param prompt: Prompt text to display.
        """
        self.print()

        value = input(prompt + '\n> ')
        confirm = None
        while confirm not in ('', 'y', 'Y', 'n'):
            self.print()
            confirm = input(f'Confirm value of:\n{value}\n(Y/n) >')
        if confirm in ('', 'y', 'Y'):
            # user is satisfied
            return value
        # ok let's try again
        return self.input(prompt)

    def __getitem__(self, key):
        """
        If the key is not in self, call :py:meth:`configure`.

        :param key: Environment variable name
        """
        if key not in self:
            self[key] = self.configure(key)
        return super().__getitem__(key)

    @property
    def profile_script(self):
        """
        Cached :py:attr:`profile_path` reader.
        """
        if self._profile_script:
            return self._profile_script

        if self.profile_path.exists():
            with self.profile_path.open('r') as f:
                self._profile_script = f.read()
        else:
            self.profile_path.touch()
            self._profile_script = ''
        return self._profile_script

    @functools.cached_property
    def profile_variables(self):
        """
        Cached environment variable parsing from :py:attr:`profile_path`.
        """
        if self._profile_variables:
            return self._profile_variables

        for line in self.profile_script.split('\n'):
            if not line.startswith('export '):
                continue
            name, value = re.findall('export ([^=]*)=(.*)', line)[0]
            value = shlex.split(value)[0]
            self._profile_variables[name] = value
        return self._profile_variables

    def configure(self, key):
        """
        Core logic to figure a variable.

        - if present in os.environ: return that
        - if parsed in profile_variables: return that
        - otherwise prompt it, with the question if any, then save it to
          :py:attr:`profile_path`
        """
        if key in self.environ:
            return self.environ[key]

        # ok, let's love our user, and try to parse the variable
        # from self.profile, after all, perhaps they are running
        # their command for the second time in the same shell
        if key in self.profile_variables:
            return self.profile_variables[key]

        prompt = self.questions.get(key, key)
        prompt = textwrap.dedent(prompt).strip()
        value = self.input(prompt)
        escaped_value = shlex.quote(value)
        with self.profile_path.open('a') as f:
            f.write(f'\nexport {key}={escaped_value}')
        self.print(
            f'Appended to {self.profile_path}:'
            f'\nexport {key}={escaped_value}'
        )
        return value

    def print(self, *args, **kwargs):
        print(*args, **kwargs)

    def delete(self, key, reason=None):
        """
        Delete a variable from everywhere, useful if an api key expired.

        :param key: Env var name to delete
        :param reason: Reason to print to the user
        """
        with self.profile_path.open('r') as f:
            lines = f.read().split('\n')

        contents = [
            line
            for line in lines
            if not line.startswith(f'export {key}=')
        ]
        if len(contents) != len(lines):
            if reason:
                print(reason)
            print(f'Removing {key} configuration')

        new_script = '\n'.join(contents)
        with self.profile_path.open('w') as f:
            f.write(new_script)
        self._profile_script = new_script
        self._profile_variables.pop(key, None)
        self.pop(key, None)
        self.environ.pop(key, None)


cfg = Configuration()
