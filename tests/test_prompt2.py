from cli2.test import autotest
from pathlib import Path
import pytest
import os

from unittest import mock
from prompt2 import cli, Model, Prompt


def test_paths():
    assert cli.cli('paths') == [
        str(Prompt.LOCAL_PATH),
        str(Prompt.USER_PATH),
    ]


@pytest.fixture
def user():
    return Path(os.getenv('PROMPT2_USER_PATH')) / 'user.txt'


@pytest.fixture
def local():
    return Path(os.getenv('PROMPT2_LOCAL_PATH')) / 'local.txt'


@pytest.fixture
def kwargs(prompt2_env, user, local):
    prompt2_env['DEBUG'] = '1'
    return dict(
        ignore=[
            str(user.parent.parent),
            str(local.parent.parent),
            str(Path(__file__).parent.parent),
        ],
        env=prompt2_env,
    )


@pytest.mark.asyncio
async def test_python(prompt2_env):
    model = Model.get()

    prompt = Prompt()
    prompt.parts.append('make a hello world in python')
    result = await model(prompt)
    assert 'To run this:' in result
    result = await model(prompt, 'wholefile')
    assert result == 'print("Hello, World!")'


def test_parsers(kwargs):
    autotest(
        'tests/prompt2/test_parsers.txt',
        'prompt2 parsers',
        **kwargs,
    )
    autotest(
        'tests/prompt2/test_parser_success.txt',
        'prompt2 parser wholefile',
        **kwargs,
    )
    autotest(
        'tests/prompt2/test_parser_fail.txt',
        'prompt2 parser',
        **kwargs,
    )


def test_crud(user, kwargs):
    autotest(
        'tests/prompt2/test_edit_user.txt',
        'prompt2 edit user',
        **kwargs,
    )
    autotest(
        'tests/prompt2/test_edit_local.txt',
        'prompt2 edit local local',
        **kwargs,
    )
    autotest(
        'tests/prompt2/test_list.txt',
        'prompt2 list',
        **kwargs,
    )
    autotest(
        'tests/prompt2/test_show_user.txt',
        'prompt2 show user',
        **kwargs,
    )
    autotest(
        'tests/prompt2/test_show_local.txt',
        'prompt2 show local',
        **kwargs,
    )
    autotest(
        'tests/prompt2/test_render_local.txt',
        'prompt2 render local',
        **kwargs,
    )
    with user.open('w') as f:
        f.write('With context {{ foo }}')
    autotest(
        'tests/prompt2/test_render_user_fail.txt',
        'prompt2 render user',
        **kwargs,
    )
    autotest(
        'tests/prompt2/test_render_user_success.txt',
        'prompt2 render user foo=bar',
        **kwargs,
    )
    autotest(
        'tests/prompt2/test_messages_user_fail.txt',
        'prompt2 messages user',
        **kwargs,
    )
    autotest(
        'tests/prompt2/test_messages_user_success.txt',
        'prompt2 messages user foo=bar',
        **kwargs,
    )
    autotest(
        'tests/prompt2/test_send_user_fail.txt',
        'prompt2 send user',
        **kwargs,
    )
    autotest(
        'tests/prompt2/test_send_user_success.txt',
        'prompt2 send user foo=bar',
        **kwargs,
    )
    with user.open('w') as f:
        f.write('Write hello world in python')
    autotest(
        'tests/prompt2/test_send_code_noparser.txt',
        'prompt2 send user',
        **kwargs,
    )
    autotest(
        'tests/prompt2/test_send_code_withparser.txt',
        'prompt2 send user wholefile',
        **kwargs,
    )
