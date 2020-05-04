import os
import sys


class EntryPoint:
    def entry_point(self):
        self.exit_code = 0
        if not self.name:
            self.name = os.path.basename(sys.argv[0])
        result = self(*sys.argv[1:])
        if result is not None:
            print(result)
        sys.exit(self.exit_code)
