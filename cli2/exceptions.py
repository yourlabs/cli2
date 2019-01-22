from .colors import RED, RESET


class Cli2Exception(Exception):
    pass


class Cli2ArgsException(Cli2Exception):
    def __init__(self, command, passed_args):
        msg = ['Got arguments:'] if len(passed_args) else []

        for i, arg in enumerate(passed_args, start=0):
            msg.append('='.join([command.required_args[i], arg]))

        if msg:
            msg.append('')

        msg.append(
            'Missing arguments: ' + ', '.join([*map(
                lambda i: f'{RED}{i}{RESET}',
                command.required_args[len(passed_args):],
            )])
        )

        super().__init__('\n'.join(msg))
