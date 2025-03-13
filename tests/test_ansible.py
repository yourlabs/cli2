import cli2
import chttpx
import httpx
import mock
import pytest
import textwrap
import yaml

import cansible


@pytest.mark.asyncio
async def test_mask(monkeypatch):
    class ActionModule(cansible.ActionBase):
        masked_keys = ['a']
        print = mock.Mock()

        async def run_async(self):
            self.result['x'] = dict(a='a', b='b', c='c', d='foo a rrr')

    module = await ActionModule.run_test_async(facts=dict(mask_keys=['b']))
    # result is untouched
    assert module.result == {'x':
        {'a': 'a', 'b': 'b', 'c': 'c', 'd': 'foo a rrr'}
    }
    # output has proper masking
    expected = "\x1b[94mx\x1b[39;49;00m:\x1b[37m\x1b[39;49;00m\n\x1b[37m    \x1b[39;49;00m\x1b[94ma\x1b[39;49;00m:\x1b[37m \x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[33m***MASKED***\x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[37m    \x1b[39;49;00m\x1b[94mb\x1b[39;49;00m:\x1b[37m \x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[33m***MASKED***\x1b[39;49;00m\x1b[33m'\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[37m    \x1b[39;49;00m\x1b[94mc\x1b[39;49;00m:\x1b[37m \x1b[39;49;00mc\x1b[37m\x1b[39;49;00m\n\x1b[37m    \x1b[39;49;00m\x1b[94md\x1b[39;49;00m:\x1b[37m \x1b[39;49;00mfoo ***MASKED*** rrr\x1b[37m\x1b[39;49;00m\n"  # noqa
    module.print.assert_called_once_with(expected, mask=False)


def test_subprocess_remote(playbook):
    playbook.task_add(
        'yourlabs.test.password_get',
        no_log=True,
    )
    result = playbook()
    expected = "foo:***MASKED***:bar\n\nansible_facts:\n\n    mask_values:\n\n    - \'***MASKED***\'\n\nsecret: \'***MASKED***\'\n\nstdout: foo:***MASKED***:bar"  # noqa
    assert expected in result['stdout']




@pytest.mark.asyncio
async def test_response_error(httpx_mock):
    class Client(chttpx.Client):
        mask_keys = ['secret']

    class Action(cansible.ActionBase):
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
    class Action(cansible.ActionBase):
        fact = cansible.Option(fact='fact', default='default fact')
        arg = cansible.Option(arg='arg', fact='arg_fact')

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

    class Action(cansible.ActionBase):
        name = cansible.Option('name')

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

    class Action(cansible.ActionBase):
        name = cansible.Option('name', 'object_name', 'Test object')

        async def run_async(self):
            self.before_set(dict(foo=1))
            self.after_set(dict(foo=2))
    await Action.run_test_async()
    expected = '\x1b[91m--- before\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[32m+++ after\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[01m\x1b[35m@@ -1 +1 @@\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[91m-foo: 1\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n\x1b[32m+foo: 2\x1b[39;49;00m\x1b[37m\x1b[39;49;00m\n'  # noqa
    _print.assert_called_once_with(expected)


@pytest.mark.asyncio
async def test_fact_set():
    class Action(cansible.ActionBase):
        foo = cansible.Option(fact='foo')

        async def run_async(self):
            self.foo = 'bar'
            assert self.foo == 'bar'

    action = await Action.run_test_async(facts=dict(foo='bar'))
    assert 'ansible_facts' not in action.result

    action = await Action.run_test_async()
    assert action.result['ansible_facts'] == dict(foo='bar')


@pytest.mark.asyncio
async def test_fact_set_mutable():
    class Action(cansible.ActionBase):
        async def run_async(self):
            assert self.mask_values is self.mask.values
            self.mask_values.add('foo')

    action = await Action.run_test_async()
    assert 'mask_values' in action.facts_values
    assert action.result['ansible_facts'] == dict(mask_values=['foo'])

    action = await Action.run_test_async(facts=dict(mask_values=['foo']))
    assert 'ansible_facts' not in action.result

    action = await Action.run_test_async(facts=dict(mask_values=['bar']))
    result = action.result['ansible_facts']['mask_values']
    assert sorted(result) == ['bar', 'foo']


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


def test_masking_ansible_story(playbook):
    with open('tests/test_ansible_masking.yml', 'r') as f:
        data = yaml.safe_load(f.read())
    playbook.tasks += data[0]['tasks']
    result = playbook()
    expected = "hello ***MASKED*** ***MASKED*** bye\n\nansible_facts:\n\n    mask_values:\n\n    - \'***MASKED***\'\n\n    - \'***MASKED***\'\n\ncmd: echo hello ***MASKED*** ***MASKED*** bye\n\nstdout: hello ***MASKED*** ***MASKED*** bye"  # noqa
    assert expected in result['stdout']
