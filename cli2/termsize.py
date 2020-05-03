import os
import subprocess


def termsize():
    if 'FORCE_TERMSIZE' in os.environ:
        return 180, 80

    try:
        rows, columns = subprocess.check_output(['stty', 'size']).split()
    except subprocess.CalledProcessError:
        return 180, 80
    return int(rows), int(columns)
