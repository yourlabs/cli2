from pathlib import Path
import os
import pytest
import sys


plugin_path = Path(__file__).parent.parent / 'tests/yourlabs/test/plugins'
sys.path.insert(0, str(plugin_path))
from action import restful_api  # noqa


# enforce localhost in our client
os.environ['URL'] = 'http://localhost:8000'


@pytest.mark.asyncio
async def test_create(httpx_mock):
    os.environ['URL'] = 'http://localhost:8000'
    httpx_mock.add_response(
        url='http://localhost:8000/objects/?name=test',
        method='GET',
        json=[]
    )
    httpx_mock.add_response(
        url='http://localhost:8000/objects/',
        method='POST',
        json=dict(
            name='test',
            id=1,
            data=dict(
                Capacity='5',
                Price='3',
            ),
        ),
    )
    module = await restful_api.ActionModule.run_test_async(
        args=dict(
            name='test',
            price='3',
            capacity='5',
        )
    )
    assert module.result['data']['id'] == 1


@pytest.mark.asyncio
async def test_update(httpx_mock):
    httpx_mock.add_response(
        is_reusable=True,
        url='http://localhost:8000/objects/?name=test',
        method='GET',
        json=[dict(
            name='test',
            id=1,
            data=dict(
                Capacity='5',
                Price='3',
            ),
        )],
    )

    # testing for idempotence
    module = await restful_api.ActionModule.run_test_async(
        args=dict(
            name='test',
            capacity='5',
            price='3',
        )
    )
    assert not module.result['changed']
    assert module.result['data']['id'] == 1

    # testing for update
    httpx_mock.add_response(
        url='http://localhost:8000/objects/1/',
        method='PUT',
        json=dict(
            name='test',
            id=1,
            data=dict(
                Capacity='6',
                Price='4',
            ),
        ),
    )

    module = await restful_api.ActionModule.run_test_async(
        args=dict(
            name='test',
            capacity='4',
            price='6',
        )
    )
    assert module.result['data']['id'] == 1
    assert module.result['changed']
