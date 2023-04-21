from .command import Command


def test_output_list_dicts(mocker):
    mocker.patch('sys.exit')
    Table = mocker.patch('cli2.entry_point.Table')
    result = [
        dict(a=1, b=2),
        dict(a=2, b=3),
    ]

    def list_output():
        return result
    cmd = Command(list_output)
    cmd.entry_point('test')
    Table.factory.assert_called_once_with(*result)
    Table.factory().print.assert_called_once_with()
