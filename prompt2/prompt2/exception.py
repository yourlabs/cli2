class Prompt2Error(Exception):
    title = 'PROMPT2 ERROR'


class NotFoundError(Exception):
    title = 'NOT FOUND'

    def __init__(self, name, searched=None):
        self.name = name
        self.searched = [str(s) for s in searched or []]
        msg = [f'{self.title}: {self.name}']

        if self.searched:
            msg += ['SEARCHED:'] + searched

        try:
            self.available = self.available_list()
        except NotImplementedError:
            self.available = None
        else:
            msg += ['AVAILABLE:'] + list(self.available)

        super().__init__(' '.join([str(x) for x in msg]))

    def available_list(self):
        raise NotImplementedError()
