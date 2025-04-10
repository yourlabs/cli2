import pytest
from pathlib import Path
import os
from cli2 import Find

@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository with test files."""
    # Initialize git repo
    os.system(f"git init {tmp_path}")

    # Create some test files and directories
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("main content")
    (tmp_path / "src" / "utils.py").write_text("utils content")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("test content")
    (tmp_path / ".gitignore").write_text("*.pyc\n__pycache__")

    # Add files to git
    os.system(f"cd {tmp_path} && git add . && git commit -m 'Initial commit'")

    return tmp_path

def test_basic_initialization():
    """Test basic Find initialization."""
    finder = Find()
    assert isinstance(finder.root, Path)
    assert finder.root.is_dir()
    assert finder.glob_include == []
    assert finder.glob_exclude == []
    assert finder.callback is None


def test_custom_root_initialization(temp_git_repo):
    """Test initialization with custom root."""
    finder = Find(root=temp_git_repo)
    assert finder.root == temp_git_repo.resolve()


def test_files_listing(temp_git_repo):
    """Test basic file listing."""
    finder = Find(root=temp_git_repo, flags='-type f')
    files = finder.run()

    file_names = {f.name for f in files}
    assert "main.py" in file_names
    assert "utils.py" in file_names
    assert "test_main.py" in file_names
    assert ".gitignore" in file_names


def test_dirs_listing(temp_git_repo):
    """Test basic directory listing."""
    finder = Find(root=temp_git_repo, flags='-type d')
    dirs = finder.run()

    dir_names = {d.name for d in dirs}
    assert "src" in dir_names
    assert "tests" in dir_names


def test_glob_include_filter(temp_git_repo):
    """Test glob include filtering."""
    finder = Find(root=temp_git_repo, glob_include=["*.py"], flags='-type f')
    files = finder.run()

    file_names = {f.name for f in files}
    assert "main.py" in file_names
    assert "utils.py" in file_names
    assert "test_main.py" in file_names
    assert ".gitignore" not in file_names


def test_glob_exclude_filter(temp_git_repo):
    """Test glob exclude filtering."""
    finder = Find(root=temp_git_repo, glob_exclude=["*test*"], flags='-type f')
    files = finder.run()

    file_names = {f.name for f in files}
    assert "main.py" in file_names
    assert "utils.py" in file_names
    assert "test_main.py" not in file_names


def test_callback(temp_git_repo):
    """Test file callback functionality."""
    called_paths = []
    def callback(filepath):
        called_paths.append(filepath)

    finder = Find(root=temp_git_repo, callback=callback, flags='-type f')
    files = finder.run()

    assert len(called_paths) == len(files)
    assert set(called_paths) == set(files)


def test_custom_directory_search(temp_git_repo):
    """Test searching from a specific directory."""
    finder = Find(root=temp_git_repo, flags='-type f')
    files = finder.run(directory=temp_git_repo / "src")

    file_names = {f.name for f in files}
    assert "main.py" in file_names
    assert "utils.py" in file_names
    assert "test_main.py" not in file_names


def test_matches_filters(temp_git_repo):
    """Test the _matches_filters method."""
    finder = Find(
        root=temp_git_repo,
        glob_include=["*.py"],
        glob_exclude=["*test*"],
    )

    assert finder._matches_filters(temp_git_repo / "src" / "main.py")
    assert finder._matches_filters(temp_git_repo / "src" / "utils.py")
    assert not finder._matches_filters(temp_git_repo / "tests" / "test_main.py")
    assert not finder._matches_filters(temp_git_repo / ".gitignore")
