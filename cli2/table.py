import os

from .colors import colors


class Column:
    def __init__(self, name, maxlength=None):
        self.name = name
        self.maxlength = maxlength or 0
        self.minlength = len(name)


class Table(list):
    def __init__(self, columns, *args, header=True):
        self.columns = [
            Column(**c)
            if isinstance(c, dict)
            else Column(c)
            for c in columns
        ]
        self.header = header
        super().__init__(args)

    def print(self, print_function=None):
        print_function = print_function or print

        # set maxlength value length and maxlength for each column based on data
        for row in self:
            for colnum, item in enumerate(row):
                data = item
                if isinstance(data, (list, tuple)):
                    color = data[0]
                    data = data[1]
                else:
                    color = ''
                    data = item
                length = len(data)
                if length > self.columns[colnum].maxlength:
                    self.columns[colnum].maxlength = length

        # shrink last column if necessary
        try:
            size = os.get_terminal_size().columns
        except:
            size = 80
        sumsize = sum([c.maxlength for c in self.columns]) + len(self.columns)
        maxsize = max([c.maxlength for c in self.columns])
        if sumsize > size:
            _ = sum([c.maxlength for c in self.columns[:-1]]) - len(self.columns)
            self.columns[-1].maxlength = size - _ - len(self.columns) - 1

        if self.header:
            line = []
            for column in self.columns:
                spaces = column.maxlength - len(column.name)
                left = int(spaces / 2)
                right = spaces - left
                line.append(
                    ' ' * left
                    + column.name
                    + ' ' * right
                )
            print_function(' '.join(line))

            line = []
            for column in self.columns:
                line.append(
                    '=' * column.maxlength
                )
            print_function(' '.join(line))

        rows = list(self)
        while rows:
            row = rows.pop(0)
            line = []
            leftovers = [[] for c in self.columns]
            for colnum, column in enumerate(self.columns):
                data = row[colnum]
                if isinstance(data, (list, tuple)):
                    color = data[0]
                    data = data[1]
                else:
                    color = ''
                    data = row[colnum]

                datawords = data.split(' ')
                words = []
                for dataword in datawords:
                    if len(' '.join(words + [dataword])) <= column.maxlength:
                        words.append(dataword)
                    else:
                        leftovers[colnum].append(dataword)
                data = ' '.join(words)
                line.append(
                    color
                    + data
                    + ' ' * (column.maxlength - len(data))
                    + colors.reset
                )
            for leftover in leftovers:
                if len(leftover):
                    rows.insert(0, [' '.join(l) for l in leftovers])
                    break
            print_function(' '.join(line))
