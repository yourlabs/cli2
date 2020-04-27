from cli2.cli import main


def test_call():
    result = main('cli2.test_node.example_function', 'x', 'y=z')
    assert "args=('x',)" in result
    assert "kwargs={'y': 'z'}" in result


def test_doc():
    result = main('cli2.test_node')
    assert 'example_function' in result

    result = main('help', 'cli2.test_node')
    assert 'example_function' in result

    result = main()
    assert 'help' in result
