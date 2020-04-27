import sys


class EntryPoint:
    def entry_point(self):
        self.exit_code = 0
        result = self(*sys.argv[1:])
        if result is not None:
            print(result)
        return self.exit_code
