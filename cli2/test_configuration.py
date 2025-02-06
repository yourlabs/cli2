import cli2
import os
import subprocess


class Configuration(cli2.Configuration):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.expected_prompts = dict()
        self.prints = []

    def input(self, prompt):
        return self.expected_prompts.pop(prompt)

    def print(self, *args, **kwargs):
        self.prints.append((args, kwargs))


def test_idempotent(tmp_path):
    profile_path = tmp_path / 'bashrc'
    cfg = Configuration(
        profile_path=profile_path,
        ENV_VAR1='What 1?',
    )

    # get something hard to escape
    value = '''foo$a#e'"'''
    cfg.expected_prompts['What 1?'] = value
    assert cfg['ENV_VAR1'] == value

    # no expected prompt here: it should parse it again from profile_path
    cfg = Configuration(
        profile_path=profile_path,
        ENV_VAR1='What 1?',
    )
    assert 'ENV_VAR1' in cfg.profile_variables
    assert cfg['ENV_VAR1'] == value

    # let's make sure we get the same value from new shells
    result = subprocess.check_output(
        f'. {profile_path} && echo $ENV_VAR1',
        shell=True,
    )
    assert result.decode().strip() == value

    # we don't like the value of the variable anymore (ie. password changed,
    # api key revoked ...), ask for a new one
    with cfg.profile_path.open('r') as f:
        before = f.read()
    assert 'export ENV_VAR1=' in before
    cfg.delete('ENV_VAR1')
    with cfg.profile_path.open('r') as f:
        after = f.read()
    assert 'export ENV_VAR1=' not in after
    assert 'export ENV_VAR1=' not in cfg.profile_script
    assert 'ENV_VAR1' not in cfg.profile_variables
    assert 'ENV_VAR1' not in cfg.environ
    assert 'ENV_VAR1' not in cfg

    # it should also find it from os.environ
    os.environ['ENV_VAR2'] = value
    cfg = Configuration(
        profile_path=profile_path,
        ENV_VAR2='What 2?',
    )
    assert cfg['ENV_VAR2'] == value

    cfg.questions['TEST'] = '''
        Test
        For
        Dedent
    '''
    cfg.expected_prompts['Test\nFor\nDedent'] = 'success'
    assert cfg['TEST'] == 'success'
    assert cfg.prints[0][0][0] == (
        f'Appended to {cfg.profile_path}:\nexport TEST=success'
    )
