import cli2
import textwrap


def test_calculate_columns():
    table = cli2.Table(  # noqa
        ['a', 'b'],
        ['foo test', 'bar'],
    )

    # large term
    columns = table.calculate_columns(termsize=80)
    assert columns[0].minlength == 4
    assert columns[0].maxlength == 8
    assert columns[1].minlength == 3
    assert columns[1].maxlength == 3

    # small term
    columns = table.calculate_columns(termsize=8)
    assert columns[0].minlength == 4
    assert columns[0].maxlength == 4
    assert columns[1].minlength == 3
    assert columns[1].maxlength == 3

    # term too small, use lowest possibility
    columns = table.calculate_columns(termsize=3)
    assert columns[0].minlength == 4
    assert columns[0].maxlength == 4
    assert columns[1].minlength == 3
    assert columns[1].maxlength == 3


def assert_table_output(table, termsize, expected):
    result = []
    table.print(
        print_function=lambda data: result.append(data),
        termsize=termsize,
    )
    result = '\n'.join(result).strip()
    assert result == textwrap.dedent(expected).strip()


def test_spaces():
    table = cli2.Table(
        ['foo test', 'bar'],
    )
    # use 2 spaces between columns when possible
    assert_table_output(table, 15, '''
        foo test  bar
    ''')
    # otherwise just 1
    assert_table_output(table, 12, '''
        foo test bar
    ''')


def test_wrap_left():
    table = cli2.Table(
        ['foo test', 'bar'],
    )
    assert_table_output(table, 8, '''
        foo  bar
        test
    ''')


def test_wrap_right():
    table = cli2.Table(
        ['bar', 'foo test'],
    )
    assert_table_output(table, 8, '''
        bar foo
            test
    ''')


def test_wrap_both():
    table = cli2.Table(
        ['bar test', 'foo test'],
    )
    assert_table_output(table, 9, '''
        bar  foo
        test test
    ''')


def test_header():
    table = cli2.Table(
        ['h1', 'h2'],
        ['=', '='],
        ['bar test', 'foo test'],
    )
    assert_table_output(table, 9, '''
        h1   h2
        ==== ====
        bar  foo
        test test
    ''')
    assert_table_output(table, 20, '''
        h1        h2
        ========  ========
        bar test  foo test
    ''')
    assert_table_output(table, 18, '''
        h1       h2
        ======== ========
        bar test foo test
    ''')


def test_factory_dicts():
    table = cli2.Table.factory(
        dict(a=1, b=2),
        dict(a=2, b=3),
    )
    assert_table_output(table, 18, '''
        a  b
        =  =
        1  2
        2  3
    ''')


def test_nonstring():
    table = cli2.Table(
        [1, False],
    )
    assert_table_output(table, 9, '''
        1  False
    ''')
