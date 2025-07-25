import cli2
from cli2.test import autotest
from pathlib import Path
import pytest
import os
import subprocess

from unittest import mock
import prompt2
from prompt2 import Model, Prompt
from prompt2.cli import cli


def test_model():
    os.environ['MODEL'] = 'litellm foo bar=1 foo=.2'
    model = Model()
    assert type(model.backend).__name__ == 'LiteLLMPlugin'
    assert model.backend.model_name == 'foo'
    assert model.backend.model_kwargs['bar'] == 1
    assert model.backend.model_kwargs['foo'] == .2
    del os.environ['MODEL']

    os.environ['MODEL_FOO'] = 'test a=b'
    model = Model('foo')
    assert type(model.backend).__name__ == 'LiteLLMPlugin'
    assert model.backend.model_name == 'test'
    assert model.backend.model_kwargs['a'] == 'b'


def test_prompt(user, local):
    with user.open('w') as f:
        f.write('hello')

    args = ['user', str(user), user]
    for arg in args:
        prompt = Prompt(arg)
        assert prompt.path == user, arg
        assert prompt.content == 'hello', arg
        assert prompt.name == 'user'


def test_paths():
    paths = cli('paths')
    assert paths[0] == str(Prompt.local_path)
    assert paths[1] == str(Prompt.user_path)


@pytest.fixture
def user(prompt2_env):
    path = Path(prompt2_env.get('PROMPT2_USER_PATH'))
    path.mkdir(parents=True, exist_ok=True)
    return path / 'user.txt'


@pytest.fixture
def local(prompt2_env):
    path = Path(prompt2_env.get('PROMPT2_LOCAL_PATH'))
    path.mkdir(parents=True, exist_ok=True)
    return path / 'local.txt'


@pytest.fixture
def kwargs(prompt2_env, user, local):
    prompt2_env['DEBUG'] = '1'
    prompt2_env['PROMPT2_PATHS_EP'] = ''
    prompt2_env['PROMPT2_PARSER_EP'] = ''
    return dict(
        ignore=[
            str(os.getcwd()),
            str(user.parent.parent),
            str(local.parent.parent),
            str(Path(prompt2.__path__[0])),
            str(Path(__file__).parent),
            r'/tmp/.*',
        ],
        env=prompt2_env,
    )


@pytest.mark.asyncio
async def test_python(prompt2_env):
    model = Model()
    prompt = Prompt(content='make a hello world in python')
    result = await model(prompt)
    assert 'a simple' in result
    result = await model(prompt, 'wholefile')
    assert result.strip() == 'print("Hello, World!")'


def test_parsers(kwargs):
    out = subprocess.check_output(
        f'{cli2.which("prompt2")} parsers',
        shell=True,
    )
    assert b'prompt2.parser:Wholefile' in out
    autotest(
        'tests/prompt2/parser_success.txt',
        'prompt2 parser wholefile',
        **kwargs,
    )
    autotest(
        'tests/prompt2/parser_fail.txt',
        'prompt2 parser',
        **kwargs,
    )


def test_ask(kwargs):
    autotest(  # ensure clean error without arguments
        'tests/prompt2/ask_fail.txt',
        'prompt2 ask',
        **kwargs,
    )
    autotest(
        'tests/prompt2/ask.txt',
        'prompt2 ask Write hello world in python',
        **kwargs,
    )


def test_command():
    from prompt2.cli import PromptCommand
    def test(model=None, parser=None):
        return model, parser
    model, parser = PromptCommand(test)()
    assert type(model.backend).__name__ == 'LiteLLMPlugin'
    assert model.backend.model_name == Model.default
    assert not parser

    os.environ['MODEL_LOL'] = 'foo temperature=test'
    try:
        model, parser = PromptCommand(test)('lol')
    except:
        raise
    else:
        assert model.backend.model_name == 'foo'
        assert model.backend.model_kwargs == dict(temperature='test')
    finally:
        del os.environ['MODEL_LOL']

    model, parser = PromptCommand(test)('parser=wholefile')
    assert type(parser).__name__.lower() == 'wholefile'


def test_crud(user, local, kwargs):
    autotest(
        'tests/prompt2/edit_user.txt',
        'prompt2 edit user',
        **kwargs,
    )
    with user.open('w') as f:
        f.write('user hello')
    autotest(
        'tests/prompt2/edit_local.txt',
        'prompt2 edit local local',
        **kwargs,
    )
    with local.open('w') as f:
        f.write('local hello')
    autotest(
        'tests/prompt2/list.txt',
        'prompt2 list',
        **kwargs,
    )
    autotest(
        'tests/prompt2/show_user.txt',
        'prompt2 show user',
        **kwargs,
    )
    autotest(
        'tests/prompt2/show_local.txt',
        'prompt2 show local',
        **kwargs,
    )
    autotest(
        'tests/prompt2/render_local.txt',
        'prompt2 render local',
        **kwargs,
    )
    with user.open('w') as f:
        f.write('With context {{ foo }}')
    autotest(
        'tests/prompt2/render_user_fail.txt',
        'prompt2 render user',
        **kwargs,
    )
    autotest(
        'tests/prompt2/render_user_success.txt',
        'prompt2 render user foo=bar',
        **kwargs,
    )
    autotest(
        'tests/prompt2/messages_user_fail.txt',
        'prompt2 messages user',
        **kwargs,
    )
    autotest(
        'tests/prompt2/messages_user_success.txt',
        'prompt2 messages user foo=bar',
        **kwargs,
    )
    autotest(
        'tests/prompt2/send_user_fail.txt',
        'prompt2 send user',
        **kwargs,
    )
    autotest(
        'tests/prompt2/send_user_success.txt',
        'prompt2 send user foo=bar',
        **kwargs,
    )
    with user.open('w') as f:
        f.write('Write hello world in python')
    autotest(
        'tests/prompt2/send_code_noparser.txt',
        'prompt2 send user',
        **kwargs,
    )
    autotest(
        'tests/prompt2/send_code_withparser.txt',
        'prompt2 send user wholefile',
        **kwargs,
    )
    out = subprocess.check_output(
        f'{cli2.which("prompt2")} send user foobar',
        shell=True,
    )
    assert b'wholefile' in out
    assert b'PARSER NOT FOUND' in out
    assert b'foobar' in out
    os.environ['MODEL_FOO'] = 'test a=b'
    autotest(
        'tests/prompt2/send_code_failmodel.txt',
        'prompt2 send user model=oaeoeau',
        **kwargs,
    )
