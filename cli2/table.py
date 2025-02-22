"""
cli2 also offers a simple table rendering data that will do it's best to word
wrap cell data so that it fits in the terminal.

This Table module behaves like a list, and is pretty simple. Its purpose is to
tabulate data and it's going to brute force output sizes until it finds a
match.

As such, it's not a good module to display really a lot of data because it
sacrifies performance for human readability.

.. code-block:: python

    cli2.Table.factory(['foo', 'bar'], ['much longer', 'test']).print()

.. code-block::

    foo          bar
    much longer  test

.. note:: This would look better with :py:mod:`~cli2.color`

.. code-block:: python

    cli2.Table.factory(dict(foo=1, bar=2), dict(foo=3, bar=4)).print()

Renders:

.. code-block::

    foo  bar
    ===  ===
    1    2
    3    4
"""

import os
import textwrap

from .colors import colors


class Column:
    """ Column object """

    def __init__(self):
        self.maxlength = 1
        self.minlength = 1


# size taken by the length of every column
def sumsize(columns):
    sumsize = sum([c.maxlength for c in columns])
    if len(columns) > 1:
        # add one space in-between each column
        sumsize += len(columns) - 1
    return sumsize


class Table(list):
    """
    Table object
    """
    def __init__(self, *args):
        super().__init__(args)

    @classmethod
    def factory(cls, *items):
        """
        Instanciate a table with a bunch of items.

        :params items: Iterable of lists or dicts or tuples
        """
        self = cls()
        first = True
        kind = None
        for item in items:
            if not kind:
                kind = type(item)
            elif kind != type(item):
                raise Exception('Data contains different types')

            if isinstance(item, (list, tuple)):
                self.append([str(item) for item in item])
            elif isinstance(item, dict):
                if first:
                    self.append([key for key in item.keys()])
                    self.append(['=' for key in item.keys()])
                    first = False
                self.append([str(value) for value in item.values()])
        return self

    def calculate_columns(self, termsize):
        """
        Calculate columns size based on termsize.
        """
        columns = self.columns = []

        for row in self:
            for colnum, item in enumerate(row):
                if len(columns) == colnum:
                    column = Column()
                    columns.append(column)
                else:
                    column = columns[colnum]

                data = item

                if isinstance(data, (list, tuple)):
                    data = data[1]
                else:
                    data = item

                data = str(data)

                minlength = max(
                    [len(word) for word in data.split(' ')]
                )
                if minlength > column.minlength:
                    column.minlength = minlength

                length = len(data)
                if length > column.maxlength:
                    column.maxlength = length

        current = -1
        done = set()
        while sumsize(columns) > termsize and len(done) < len(columns):
            current = current if current >= 0 else len(columns) - 1
            if current not in done:
                # Let's start shrinking columns from the last
                minlength = columns[current].minlength
                maxlength = columns[current].maxlength
                if maxlength - 1 > minlength:
                    columns[current].maxlength = maxlength - 1
                else:
                    columns[current].maxlength = minlength
                    done.add(columns[current])
            current -= 1

        return columns

    def print(self, print_function=None, termsize=None):
        """
        Print the table.
        """
        print_function = print_function or print
        if not termsize:
            try:
                termsize = os.get_terminal_size().columns
            except:  # noqa
                termsize = 80
        columns = self.calculate_columns(termsize=termsize)

        # separate columns with 2 spaces if possible
        if sumsize(columns) + (len(columns) - 1) * 2 <= termsize:
            numspaces = 2
        else:
            numspaces = 1

        rows = list(self)
        while rows:
            row = rows.pop(0)
            line = []
            leftovers = ['' for c in columns]
            for colnum, column in enumerate(columns):
                data = row[colnum]
                if isinstance(data, (list, tuple)):
                    color = data[0]
                    data = data[1]
                else:
                    color = ''
                    data = row[colnum]
                data = str(data)

                wrapped = textwrap.wrap(data, column.maxlength)
                words = wrapped[0] if wrapped else ''
                if words == '=':
                    words = '=' * column.maxlength
                line.append(words)
                if colnum + 1 < len(columns):
                    # add spaces
                    line[-1] += ' ' * (column.maxlength - len(words))
                if len(wrapped) > 1:
                    leftovers[colnum] = ' '.join(wrapped[1:])
                if color:
                    line[-1] = color + line[-1] + colors.reset
            for leftover in leftovers:
                if len(leftover):
                    rows.insert(0, leftovers)
                    break
            print_function((' ' * numspaces).join(line))
