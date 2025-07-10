import os
import subprocess
os.environ['FORCE_COLOR'] = '1'
os.environ['ANSIBLE_FORCE_COLOR'] = '1'
os.environ['CLI2_THEME'] = 'standard'

# or log tests
os.environ['NO_TIMESTAMPER'] = '1'

# for traceback test
import cli2
os.environ['PROJECT_PATH'] = str(cli2.__path__[0])

for key in os.environ.keys():
    if key.startswith('MODEL'):
        del os.environ[key]

result = subprocess.check_output('''
mkdir -p ~/.ansible/collections/ansible_collections/yourlabs
ln -sfn $PWD/tests/yourlabs/test ~/.ansible/collections/ansible_collections/yourlabs/test
''', shell=True)
