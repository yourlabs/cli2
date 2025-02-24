from cli2 import ansible
import pytest
import os


def test_story():
    variables = ansible.Variables(
        root_path=os.path.dirname(__file__),
        pass_path=os.path.dirname(__file__) + '/vault_pass',
    )
    variables.read('variables.yml')
    assert variables['variables.yml'] == dict(foo='bar', vaulted='foobar')
    assert variables['variables_vault.yml'] == dict(bar='foo')


def test_exceptions():
    variables = ansible.Variables()
    with pytest.raises(Exception) as exc:
        variables['variables.yml']
    assert exc.value.args == (
        'variables.yml must be absolute if root_path not set',
    )

    with pytest.raises(Exception) as exc:
        variables['/variables_vault.yml']
    assert exc.value.args == ('/variables_vault.yml does not exist',)

    variables = ansible.Variables(root_path=os.path.dirname(__file__))
    with pytest.raises(Exception) as exc:
        variables['variables_vault.yml']
    assert exc.value.args == ('Vault password required in pass_path',)

    variables = ansible.Variables(
        root_path=os.path.dirname(__file__),
        pass_path='/does/not/exist',
    )
    with pytest.raises(Exception) as exc:
        variables['variables_vault.yml']
    assert exc.value.args == ('/does/not/exist does not exist',)
