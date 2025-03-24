import cli2
import chttpx
import datetime
import pytest
import yaml
from pathlib import Path


def pytest_addoption(parser):
    parser.addoption(
        "--chttpx-rewrite",
        action="store_true",
        default=False,
        help="Rewrite all chttpx fixtures"
    )
    parser.addoption(
        "--chttpx-live",
        action="store_true",
        default=False,
        help="Run chttpx against real server instead of mock"
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "chttpx_mock: Automatic chttpx mocking"
    )


def pytest_runtest_setup(item):
    if 'chttpx_mock' in item.keywords:
        # Ensure the fixture is requested for this test
        item.fixturenames.append('chttpx_mock')


@pytest.fixture(autouse=True)
def zero_retries():
    # don't retry by default with chttpx
    chttpx.Handler.tries_default = 0


@pytest.fixture
def chttpx_vars():
    return dict()


@pytest.fixture
def chttpx_mock(chttpx_vars, request, tmp_path):
    if (
        'httpx_mock' in request.fixturenames
        or request.config.getoption('--chttpx-live')
    ):
        yield
    else:
        yield from _fixture_handle(chttpx_vars, request, tmp_path)


@pytest.fixture
def ts():
    return int(datetime.datetime.now().timestamp())


def _fixture_handle(chttpx_vars, request, tmp_path):
    test_name = request.node.nodeid.replace('/', '_')

    path = Path(request.fspath)
    fixtures_path = path.parent / 'fixtures'
    fixtures_path.mkdir(exist_ok=True, parents=True)
    fixture_path = fixtures_path / f'{test_name}.yaml'

    if (
        fixture_path.exists()
        and not request.config.getoption('--chttpx-rewrite')
    ):
        # load fixture into httpx_mock
        with fixture_path.open('r') as f:
            entries = yaml.safe_load(f.read())

        chttpx_vars.update(entries[0])

        httpx_mock = request.getfixturevalue('httpx_mock')
        for entry in entries[1:]:
            if 'request' in entry and 'response' in entry:
                kwargs = dict(
                    url=entry['request']['url'],
                    method=entry['request']['method'],
                    status_code=int(entry['response']['status_code']),
                )
                if 'json' in entry['request']:
                    kwargs['match_json'] = entry['request']['json']
                if 'json' in entry['response']:
                    kwargs['json'] = entry['response']['json']
                httpx_mock.add_response(**kwargs)

    log_path = tmp_path / test_name
    cli2.configure(str(log_path))

    yield  # Test runs here

    if (
        request.config.getoption('--chttpx-rewrite')
        or not fixture_path.exists()
    ):
        # create a fixture
        data = [chttpx_vars]
        with log_path.open('r') as f:
            data += cli2.parse(f.read())

        if data:
            with fixture_path.open('w+') as f:
                f.write(yaml.dump(data))
