
def main(*args, **kwargs):
    print(f'Args: {args}')
    print(f'Kwargs: {kwargs}')

    from clilabs import context
    print(f'Context args: {context.args}')
    print(f'Context kwagrs: {context.kwargs}')
