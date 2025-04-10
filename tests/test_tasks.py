import cli2
import pytest


class PromptTask(cli2.Task):
    def __init__(self, name, template, parser=None):
        self.template = template
        self.parser = parser
        super().__init__(name)

    async def run(self, executor, context):
        return f'processed {self.name}'


@pytest.mark.asyncio
async def test_tasks():
    def exc_sync(executor, context):
        raise Exception('sync failure')

    async def exc_async(executor, context):
        raise Exception('async failure')

    workflow = cli2.TaskQueue(
        'Inspect project',
        cli2.ParallelTaskGroup(
            'Code style',
            cli2.CallbackTask(
                'Code style files',
                exc_async,
            ),
            cli2.CallbackTask(
                'Get code style',
                lambda e, c: 'runs anyway',
            ),
        ),
        cli2.SerialTaskGroup(
            'Testing',
            cli2.CallbackTask(
                'Testing files',
                exc_sync,
            ),
            cli2.CallbackTask(
                'Get testing directives',
                lambda e, c: 'must not run'
            ),
        )
    )
    result = await workflow.run()
    assert isinstance(result['code_style_files'], Exception)
    assert result['get_code_style'] == 'runs anyway'
    assert isinstance(result['testing_files'], Exception)
    assert len(result) == 3
