import cli2
import mock
import pytest
import textwrap
import yaml

from cli2 import ansible


@pytest.mark.asyncio
async def test_option():
    class Action(ansible.ActionBase):
        name = ansible.Option('name', 'object_name', 'Test object')

        async def run_async(self):
            self.result['name'] = self.name

    module = await Action.run_test_async(args=dict(name='foo'))
    assert module.result['name'] == 'foo'

    module = await Action.run_test_async(facts=dict(object_name='foo'))
    assert module.result['name'] == 'foo'

    module = await Action.run_test_async()
    assert module.result['name'] == 'Test object'

    class Action(ansible.ActionBase):
        name = ansible.Option('name', 'object_name')

        async def run_async(self):
            self.result['name'] = self.name

    module = await Action.run_test_async(fail=True)
    assert module.result == dict(
        failed=True,
        error="Missing arg `name` or fact `object_name`",
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
