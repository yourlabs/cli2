import os
import subprocess
os.environ['FORCE_COLOR'] = '1'
os.environ['CLI2_THEME'] = 'standard'

result = subprocess.check_output('''
mkdir -p ~/.ansible/collections/ansible_collections/yourlabs
ln -sfn $PWD/tests/yourlabs/test ~/.ansible/collections/ansible_collections/yourlabs/test
''', shell=True)
