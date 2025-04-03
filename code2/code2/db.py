"""
.. envvar:: CODE2_DB

    playhouse.db_url connection string
"""

import cli2

from playhouse.db_url import connect

db = connect(cli2.cfg['CODE2_DB'])
