import flow2
import pytest
import textwrap
from unittest import mock


@pytest.mark.asyncio
async def test_context():
    task = flow2.SerialTaskGroup(
        'Inspect',
        flow2.CallbackTask(
            'Initial',
            lambda c: 'first',
        ),
        flow2.CallbackTask(
            'Next',
            lambda c: f'next{c["initial"]}',
            output='next2',
        ),
    )
    result = await task.process()
    assert result == dict(initial='first', next2='nextfirst')


@pytest.mark.asyncio
async def test_exceptions():
    def exc_sync(context):
        raise Exception('sync failure')

    async def exc_async(context):
        raise Exception('async failure')

    workflow = flow2.SerialTaskGroup(
        'Inspect project',
        flow2.ParallelTaskGroup(
            'Code style',
            flow2.CallbackTask(
                'Code style files',
                exc_async,
            ),
            flow2.CallbackTask(
                'Get code style',
                lambda c: 'runs anyway',
            ),
        ),
        flow2.SerialTaskGroup(
            'Testing',
            flow2.CallbackTask(
                'Testing files',
                exc_sync,
            ),
            flow2.CallbackTask(
                'Get testing directives',
                lambda c: 'must not run'
            ),
        )
    )
    result = await workflow.process()
    assert isinstance(result['code_style_files'], Exception)
    assert result['get_code_style'] == 'runs anyway'
    assert isinstance(result['testing_files'], Exception)
    assert len(result) == 4


@pytest.mark.asyncio
async def test_plugin_dict(monkeypatch):
    class TestFlow(flow2.Flow):
        plugins = dict(test=mock.Mock(), serial=flow2.SerialTaskGroup)
    flow = TestFlow()

    tsk = await flow.data_to_task(
        dict(plugin='test', content='mycontent', name='myname'),
    )
    flow.plugins['test'].assert_called_once_with(
        'myname', content='mycontent',
    )
    flow.plugins['test'].reset_mock()

    tsk = await flow.data_to_task(
        dict(
            plugin='serial',
            tasks=[
                dict(plugin='test', content='c1', name='t1'),
                dict(plugin='test', content='c2', name='t2'),
            ],
        ),
    )
    assert isinstance(tsk, flow2.SerialTaskGroup)
    assert len(tsk.tasks) == 2
    assert flow.plugins['test'].call_args_list == [
        mock.call('t1', content='c1'),
        mock.call('t2', content='c2'),
    ]
