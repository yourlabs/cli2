from cli2.test import autotest
from pathlib import Path
import pytest
import os

from unittest import mock
from prompt2 import cli, Model, Prompt


def test_model():
    os.environ['MODEL'] = 'litellm foo bar=1 foo=.2'
    model = Model()
    assert type(model.backend).__name__ == 'LiteLLMBackend'
    assert model.backend.model_name == 'foo'
    assert model.backend.model_kwargs['bar'] == 1
    assert model.backend.model_kwargs['foo'] == .2
    del os.environ['MODEL']

    os.environ['MODEL_FOO'] = 'test a=b'
    model = Model('foo')
    assert type(model.backend).__name__ == 'LiteLLMBackend'
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
    paths = cli.cli('paths')
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
    model = Model()
    prompt = Prompt(content='make a hello world in python')
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


def test_ask(kwargs):
    autotest(
        'tests/prompt2/test_ask.txt',
        'prompt2 ask Write hello world in python',
        **kwargs,
    )


def test_command():
    from prompt2.cli import PromptCommand
    def test(model=None, parser=None):
        return model, parser
    model, parser = PromptCommand(test)()
    assert type(model.backend).__name__ == 'LiteLLMBackend'
    assert model.backend.model_name == Model.default
    assert not parser

    os.environ['MODEL_LOL'] = 'foo temperature=test'
    model, parser = PromptCommand(test)('lol')
    assert model.backend.model_name == 'foo'
    assert model.backend.model_kwargs == dict(temperature='test')

    model, parser = PromptCommand(test)('parser=wholefile')
    assert type(parser).__name__.lower() == 'wholefile'


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
    autotest(
        'tests/prompt2/test_send_code_failparser.txt',
        'prompt2 send user foeuau',
        **kwargs,
    )
    os.environ['MODEL_FOO'] = 'test a=b'
    autotest(
        'tests/prompt2/test_send_code_failmodel.txt',
        'prompt2 send user model=oaeoeau',
        **kwargs,
    )
