from .console_script import ConsoleScript
from .parser import Parser



def test_parser():
    def foo():
        pass
    script = ConsoleScript().add_commands(foo)
