"""
Effecient git-aware file finder with filtering capabilities.

Uses Linux commands: find, comm and git-ignore for an efficient path walker.

Example usage:

.. code-block:: python

    # Simple usage with default root
    finder = cli2.Find(flags='-type f')

    # Usage with filters and callback
    def callback(filepath):
        print(f"Found: {filepath}")

    finder = cli2.Find(
        root="/path/to/repo",
        glob_include=['*.py'],
        glob_exclude=['*test*'],
        callback=callback
    )
    files = finder.run()
"""
from fnmatch import fnmatch
from pathlib import Path
import os
import subprocess


class Find:
    """
    A class to walk through files and directories not ignored by git with
    optional filtering.

    .. py:attribute:: root

        Root directory for file operations

    .. py:attribute:: glob_include

        Optional list of glob patterns to include

    .. py:attribute:: glob_exclude

        Optional list of glob patterns to exclude

    .. py:attribute:: callback

        Optional callback function called for each file or directory

    .. py:attribute:: flags

        Set this to '-type f' to limit find to files or example.
    """

    def __init__(
        self,
        root=None,
        glob_include=None,
        glob_exclude=None,
        callback=None,
        flags='',
    ):
        """
        Initialize Find with optional root directory, filters, and callback.

        :param root: Root directory (defaults to current working directory if
                     not specified)
        :type root: str or pathlib.Path or None
        :param glob_include: List of glob patterns to include
        :type glob_include: list or None
        :param glob_exclude: List of glob patterns to exclude
        :type glob_exclude: list or None
        :param callback: Function to call for each file or directory
        :type callback: callable or None
        :param flags: Arguments for the fing command.
        """
        self.root = Path(os.getcwd() if root is None else root).resolve()
        self.glob_include = glob_include if glob_include is not None else []
        self.glob_exclude = glob_exclude if glob_exclude is not None else []
        self.callback = callback
        self.flags = flags

    def _matches_filters(self, filepath):
        """
        Check if a file or directory matches the include/exclude filters.

        :param filepath: Path to check against filters
        :type filepath: pathlib.Path
        :return: True if path should be included, False otherwise
        :rtype: bool
        """
        filepath_str = str(filepath.relative_to(self.root))

        if self.glob_include:
            if not any(
                fnmatch(filepath_str, pattern) for pattern in self.glob_include
            ):
                return False

        if self.glob_exclude:
            if any(
                fnmatch(filepath_str, pattern) for pattern in self.glob_exclude
            ):
                return False

        return True

    def run(self, directory=None, relative=True):
        """
        Actually run the find command.

        :param directory: str or Path, or None to use self.root
        :param relative: Wether to return relative paths
        """
        base_path = Path(directory).resolve() if directory else self.root

        cmd = ' '.join([
            f'comm -23 <(find . {self.flags} | sort)',
            f'<(find . {self.flags} | git check-ignore --stdin | sort)',
        ])
        stdout = subprocess.check_output(
            cmd,
            shell=True,
            stderr=subprocess.STDOUT,
            cwd=str(base_path)
        )

        results = []
        for line in stdout.splitlines():
            if not line.strip():
                continue

            filepath = (base_path / line.decode().strip()).resolve()

            if (
                not self.glob_include and not self.glob_exclude
            ) or self._matches_filters(filepath):
                if relative:
                    filepath = filepath.relative_to(base_path)
                results.append(filepath)
                if self.callback:
                    self.callback(filepath)

        return results
