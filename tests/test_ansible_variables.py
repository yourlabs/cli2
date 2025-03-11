import cansible
import pytest
import os


def test_story():
    variables = cansible.Variables(
        root_path=os.path.dirname(__file__),
        pass_path=os.path.dirname(__file__) + '/vault_pass',
    )
    variables.read('variables.yml')
    assert variables['variables.yml'] == dict(foo='bar', vaulted='foobar')
    assert variables['variables_vault.yml'] == dict(bar='foo')


def test_unresolvable_path_error():
    variables = cansible.Variables()
    with pytest.raises(cansible.UnresolvablePathError) as exc:
        variables['variables.yml']
    assert exc.value.args == (
        'variables.yml must be absolute if root_path not set',
    )


def test_path_not_found_error():
    variables = cansible.Variables()
    with pytest.raises(cansible.PathNotFoundError) as exc:
        variables['/nonexistent.yml']
    assert exc.value.args == ('/nonexistent.yml does not exist',)


def test_vault_password_required_error():
    variables = cansible.Variables(root_path=os.path.dirname(__file__))
    with pytest.raises(cansible.VaultPasswordFileRequiredError) as exc:
        variables['variables_vault.yml']
    assert exc.value.args == ('Vault password required in pass_path',)


def test_vault_password_file_not_found_error():
    variables = cansible.Variables(
        root_path=os.path.dirname(__file__),
        pass_path='/does/not/exist',
    )
    with pytest.raises(cansible.VaultPasswordFileNotFoundError) as exc:
        variables['variables_vault.yml']
    assert exc.value.args == ('/does/not/exist does not exist',)
