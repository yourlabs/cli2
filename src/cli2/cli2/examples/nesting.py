import cli2
from .example_obj import cli as example_cli

cli = cli2.Group('test')
cli['cli2-example'] = example_cli
