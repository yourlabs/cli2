"""
Effecient git-aware file finder with filtering capabilities.

Uses Linux commands: find, comm and git-ignore for an efficient path walker.

Example usage:

.. code-block:: python

    # Simple usage with default root
    finder = cli2.Find()
    files = finder.files()
    dirs = finder.dirs()

    # Usage with filters and callback
    def callback(filepath):
        print(f"Found: {filepath}")

    finder = cli2.Find(
        root="/path/to/repo",
        glob_include=['*.py'],
        glob_exclude=['*test*'],
        file_callback=callback
    )
    files = finder.files()
    dirs = finder.dirs()
"""
import cli2
from fnmatch import fnmatch
from pathlib import Path
import os


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

    .. py:attribute:: file_callback

        Optional callback function called for each file or directory
    """

    def __init__(
        self,
        root=None,
        glob_include=None,
        glob_exclude=None,
        file_callback=None,
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
        :param file_callback: Function to call for each file or directory
        :type file_callback: callable or None
        """
        self.root = Path(root if root is not None else os.getcwd()).resolve()
        self.glob_include = glob_include if glob_include is not None else []
        self.glob_exclude = glob_exclude if glob_exclude is not None else []
        self.file_callback = file_callback

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

    def files(self, directory=None):
        """
        List files not ignored by git, applying filters and callback.

        :param directory: Directory to start search from (defaults to root if
                          not specified)
        :type directory: str or pathlib.Path or None
        :return: List of Path objects for files not ignored by git that match
                 filters
        :rtype: list
        :raises RuntimeError: If the git command fails
        """
        base_path = Path(directory).resolve() if directory else self.root

        cmd = ' '.join([
            f'comm -23 <(find {base_path} -type f | sort)',
            f'<(find {base_path} -type f | git check-ignore --stdin | sort)'
        ])
        proc = cli2.Proc("bash", "-c", cmd).wait()

        if proc.rc != 0:
            raise RuntimeError(
                f"Command failed with return code {proc.rc}: {proc.stderr}"
            )

        files = []
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue

            filepath = (base_path / line.strip()).resolve()

            if (
                not self.glob_include and not self.glob_exclude
            ) or self._matches_filters(filepath):
                files.append(filepath)
                if self.file_callback:
                    self.file_callback(filepath)

        return files

    def dirs(self, directory=None):
        """
        List directories not ignored by git, applying filters and callback.

        :param directory: Directory to start search from (defaults to root if
                          not specified)
        :type directory: str or pathlib.Path or None
        :return: List of Path objects for directories not ignored by git that
                 match filters
        :rtype: list
        :raises RuntimeError: If the git command fails
        """
        base_path = Path(directory).resolve() if directory else self.root

        cmd = ' '.join([
            f'comm -23 <(find {base_path} -type d | sort)',
            f'<(find {base_path} -type d | git check-ignore --stdin | sort)'
        ])
        proc = cli2.Proc("bash", "-c", cmd).wait()

        if proc.rc != 0:
            raise RuntimeError(
                f"Command failed with return code {proc.rc}: {proc.stderr}"
            )

        dirs = []
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue

            dirpath = (base_path / line.strip()).resolve()

            if dirpath == base_path:
                continue

            if (
                not self.glob_include and not self.glob_exclude
            ) or self._matches_filters(dirpath):
                dirs.append(dirpath)
                if self.file_callback:
                    self.file_callback(dirpath)

        return dirs
