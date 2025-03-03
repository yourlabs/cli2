import cli2
import httpx
import mock
import pytest
import textwrap
import yaml

from cli2 import ansible


class ActionModule(ansible.ActionBase):
    mask = ['a']

    async def run_async(self):
        self.result['x'] = dict(a='a', b='b', c='c', d='foo a rrr')


@pytest.mark.asyncio
async def test_mask(monkeypatch):
    printer = mock.Mock()
    monkeypatch.setattr(ActionModule, 'print', printer)
    module = await ActionModule.run_test_async(facts=dict(mask=['b']))
    # result is untouched
    assert module.result == {'x':
        {'a': 'a', 'b': 'b', 'c': 'c', 'd': 'foo a rrr'}
    }
    # output has proper masking
    expected = "\x1b[94mx\x1b[39;49;00m:\x1b[37m\x1b[39;49;00m\n\x1b[37m    \x1b[39;49;00m\x1b[94ma\x1b[39;49;00m:\x1b[37m \x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[33m***MASKED***\x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[37m    \x1b[39;49;00m\x1b[94mb\x1b[39;49;00m:\x1b[37m \x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[33m***MASKED***\x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[37m    \x1b[39;49;00m\x1b[94mc\x1b[39;49;00m:\x1b[37m \x1b[39;49;00mc\x1b[37m\x1b[39;49;00m\n\x1b[37m    \x1b[39;49;00m\x1b[94md\x1b[39;49;00m:\x1b[37m \x1b[39;49;00mfoo ***MASKED*** rrr\x1b[37m\x1b[39;49;00m\n"  # noqa
    printer.assert_called_once_with(expected)


@pytest.mark.asyncio
async def test_response_error(httpx_mock):
    class Client(cli2.Client):
        mask = ['secret']

    class Action(ansible.ActionBase):
        async def client_factory(self):
            return Client(base_url='http://foo')

        async def run_async(self):
            await self.client.post('/', json=dict(secret=2, foo=1))

    httpx_mock.add_response(
        url='http://foo/',
        status_code=400,
        json=dict(foo=2, secret=3),
    )
    module = await Action.run_test_async(fail=True)
    assert module.result == {
        'failed': True,
        'method': 'POST',
        'url': 'http://foo/',
        'status_code': '400',
        'response_json': {'foo': 2, 'secret': '***MASKED***'},
        'request_json': {'secret': '***MASKED***', 'foo': 1}
    }


@pytest.mark.asyncio
async def test_option():
    class Action(ansible.ActionBase):
        fact = ansible.Option(fact='fact', default='default fact')
        arg = ansible.Option(arg='arg', fact='arg_fact')

        async def run_async(self):
            self.result['arg'] = self.arg
            self.result['fact'] = self.fact


    # test setting arg and fact
    module = await Action.run_test_async(
        args=dict(arg='arg'),
        facts=dict(fact='fact'),
    )
    assert module.result['arg'] == 'arg'
    assert module.result['fact'] == 'fact'

    # test default
    module = await Action.run_test_async(
        args=dict(arg='arg'),
    )
    assert module.result['arg'] == 'arg'
    assert module.result['fact'] == 'default fact'

    # test failing for missing default
    module = await Action.run_test_async(fail=True)
    assert module.result == dict(
        failed=True,
        error="Missing arg `arg` or fact `arg_fact`",
    )

    class Action(ansible.ActionBase):
        name = ansible.Option('name')

        async def run_async(self):
            self.result['name'] = self.name

    module = await Action.run_test_async(fail=True)
    assert module.result == dict(
        failed=True,
        error="Missing arg `name`",
    )


@pytest.mark.asyncio
async def test_diff(monkeypatch):
    _print = mock.Mock()
    monkeypatch.setattr(cli2.display, '_print', _print)

    class Action(ansible.ActionBase):
        name = ansible.Option('name', 'object_name', 'Test object')

        async def run_async(self):
            self.before_set(dict(foo=1))
            self.after_set(dict(foo=2))
    await Action.run_test_async()
    expected = '\x1b[91m--- before\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[32m+++ after\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[01m\x1b[35m@@ -1 +1 @@\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[91m-foo: 1\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[32m+foo: 2\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n'  # noqa
    _print.assert_called_once_with(expected)


def test_playbook_render(playbook):
    assert playbook.name == 'test_playbook_render'
    playbook.task_add(
        'yourlabs.test.restful_api',
        args=dict(
            name='test',
            price='1',
            capacity='2',
        ),
        register='test_register',
    )
    assert playbook.yaml
    role_tasks = [
        dict(debug=dict(msg='hello')),
        dict(debug=dict(msg='bye')),
    ]
    playbook.role_add(
        'foo',
        *role_tasks,
        bar='test',
    )
    assert playbook.yaml
    with (playbook.root / 'foo/tasks/main.yml').open('r') as f:
        assert yaml.safe_load(f.read()) == role_tasks
    playbook.vars['test'] = 'hello'
    assert playbook.yaml.strip() == textwrap.dedent(f'''
    - hosts: localhost
      vars:
        test: hello
      roles:
      - role: {playbook.root}/foo
        bar: test
      tasks:
      - yourlabs.test.restful_api:
          name: test
          price: '1'
          capacity: '2'
        register: test_register
    ''').strip()


def test_playbook_exec(playbook):
    playbook.task_add('debug', args=dict(msg='hello'))
    result = playbook()
    assert result['changed'] == 0
    assert result['ok'] == 2
