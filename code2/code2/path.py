import os
from pathlib import Path
import subprocess
from concurrent.futures import ThreadPoolExecutor
import fnmatch
import cli2

class PathWalker:
    def __init__(self, root_path, max_workers=None, include_globs=None, exclude_globs=None):
        """Initialize PathWalker with root directory, thread pool, and glob filters."""
        self.root_path = Path(root_path).resolve()
        self._ignore_cache = {}  # Cache for git ignore results
        self._is_git_repo = self._check_git_repo()  # Check if we're in a git repo
        if max_workers is None:
            cpu_count = os.cpu_count() or 4
            max_workers = cpu_count * 2
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self.include_globs = include_globs or []
        self.exclude_globs = exclude_globs or []

    def __del__(self):
        """Clean up thread pool on object deletion."""
        self._executor.shutdown()

    def _check_git_repo(self):
        """Check if the root_path is within a git repository."""
        try:
            proc = cli2.Proc('git', 'rev-parse', '--is-inside-work-tree', cwd=self.root_path).wait_sync()
            return proc.rc == 0 and proc.stdout.strip() == 'true'
        except subprocess.SubprocessError:
            return False

    def _matches_globs(self, path):
        """Check if a path matches the include/exclude glob patterns."""
        rel_path = str(Path(path).relative_to(self.root_path))
        if self.include_globs:
            if not any(fnmatch.fnmatch(rel_path, pattern) for pattern in self.include_globs):
                return False
        if self.exclude_globs:
            if any(fnmatch.fnmatch(rel_path, pattern) for pattern in self.exclude_globs):
                return False
        return True

    def _check_git_ignore(self, path):
        """Helper method to run git check-ignore synchronously in a thread."""
        if not self._is_git_repo:
            return False  # If not a git repo, assume nothing is ignored

        try:
            # Ensure path is absolute and resolve any symlinks
            abs_path = Path(path).resolve()
            rel_path = str(abs_path.relative_to(self.root_path))
            proc = cli2.Proc(
                'git', 'check-ignore', '-q', rel_path,
                cwd=self.root_path
            ).wait_sync()
            is_ignored = proc.rc == 0
            # Optional debug output (comment out in production)
            # print(f"Debug: {rel_path} -> ignored: {is_ignored}")
            return is_ignored
        except (ValueError, subprocess.SubprocessError):
            # If path can't be made relative or command fails, assume not ignored
            return False

    def is_git_ignored(self, path):
        """Check if a path would be ignored by git using threaded execution."""
        path_str = str(Path(path).resolve())  # Use resolved absolute path as cache key
        if path_str in self._ignore_cache:
            return self._ignore_cache[path_str]

        future = self._executor.submit(self._check_git_ignore, path)
        result = future.result()
        self._ignore_cache[path_str] = result
        return result

    def walk_dirs(self, recursive=True, gitignore=True):
        """Walk directories and return a list of directory paths."""
        dirs_list = []

        if recursive:
            for root, dirs, _ in os.walk(self.root_path):
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    if gitignore and self.is_git_ignored(dir_path):
                        continue
                    if not self._matches_globs(dir_path):
                        continue
                    dirs_list.append(dir_path)
        else:
            for item in os.listdir(self.root_path):
                item_path = os.path.join(self.root_path, item)
                if os.path.isdir(item_path):
                    if gitignore and self.is_git_ignored(item_path):
                        continue
                    if not self._matches_globs(item_path):
                        continue
                    dirs_list.append(item_path)

        return sorted(dirs_list)

    def walk_files(self, extensions=None, recursive=True, gitignore=True):
        """Walk files and return a list of file paths."""
        files_list = []

        if recursive:
            for root, _, files in os.walk(self.root_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    if gitignore and self.is_git_ignored(file_path):
                        continue
                    if not self._matches_globs(file_path):
                        continue
                    if extensions:
                        if not any(file_path.endswith(ext) for ext in extensions):
                            continue
                    files_list.append(file_path)
        else:
            for item in os.listdir(self.root_path):
                item_path = os.path.join(self.root_path, item)
                if os.path.isfile(item_path):
                    if gitignore and self.is_git_ignored(item_path):
                        continue
                    if not self._matches_globs(item_path):
                        continue
                    if extensions:
                        if not any(item_path.endswith(ext) for ext in extensions):
                            continue
                    files_list.append(item_path)

        return sorted(files_list)


def dirs(path, recursive=True, gitignore=True, include_globs=None, exclude_globs=None):
    """
    Show the list of directories within a path.

    Renders::
        Available directories:
        - path/to/directory1
        - path/to/directory2

    :param path: Path to walk
    :param recursive: Whether to walk recursively
    :param gitignore: Whether to skip paths that would be ignored by git
    :param include_globs: List of glob patterns to include
    :param exclude_globs: List of glob patterns to exclude
    """
    walker = PathWalker(path, include_globs=include_globs, exclude_globs=exclude_globs)
    dir_list = walker.walk_dirs(recursive=recursive, gitignore=gitignore)

    if not dir_list:
        return "No directories found."

    output = ["Available directories:"]
    output.extend(f"- {d}" for d in dir_list)
    return "\n".join(output)


def files(path, extensions=None, recursive=True, gitignore=True, include_globs=None, exclude_globs=None):
    """
    Show the list of files within a path.

    Renders::
        Available files:
        - path/to/file1
        - path/to/file2

    :param path: Path to walk
    :param extensions: Optional list of file extensions to filter by
    :param recursive: Whether to walk recursively
    :param gitignore: Whether to skip paths that would be ignored by git
    :param include_globs: List of glob patterns to include
    :param exclude_globs: List of glob patterns to exclude
    """
    walker = PathWalker(path, include_globs=include_globs, exclude_globs=exclude_globs)
    file_list = walker.walk_files(
        extensions=extensions,
        recursive=recursive,
        gitignore=gitignore
    )

    if not file_list:
        return "No files found."

    output = ["Available files:"]
    output.extend(f"- {f}" for f in file_list)
    return "\n".join(output)


# Example usage:
if __name__ == "__main__":
    path = "."

    print("Directories:")
    print(dirs(path))

    print("\nFiles (only '*.py'):")
    print(files(path, extensions=[".py"]))
