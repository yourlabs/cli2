from pathlib import Path
import os
import pytest


@pytest.fixture(autouse=True)
def prompt2_env(request, tmp_path):
    path = Path(request.fspath)
    fixtures_path = path.parent / 'fixtures/prompt2'
    env = dict(
        PROMPT2_CACHE_PATH=str(fixtures_path / 'cache'),
        PROMPT2_USER_PATH=str(tmp_path / 'prompts_user'),
        PROMPT2_LOCAL_PATH=str(tmp_path / 'prompts_local'),
        EDITOR='cat',
        NO_TIMESTAMPER='1',
    )
    os.environ.update(env)
    return env
