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
def ts():
    return int(datetime.datetime.now().timestamp())


@pytest.fixture
def chttpx_fixture_path(request):
    test_name = request.node.nodeid.replace('/', '_')
    path = Path(request.fspath)
    fixtures_path = path.parent / 'fixtures'
    fixtures_path.mkdir(exist_ok=True, parents=True)
    return fixtures_path / f'{test_name}.yaml'


class Fixture:
    def __init__(self, path):
        self.path = path
        self.vars = dict()
        self.requests = []

    def read(self):
        with self.path.open('r') as f:
            data = yaml.safe_load(f.read())
        self.vars = data[0]
        self.requests = data[1:]

    def mock(self, httpx_mock):
        for entry in self.requests:
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

    def write(self):
        if self.vars and self.requests:
            data = [self.vars] + self.requests
            with self.path.open('w+') as f:
                f.write(yaml.dump(data))


@pytest.fixture
def chttpx_fixture(chttpx_fixture_path):
    fixture = Fixture(chttpx_fixture_path)
    if fixture.path.exists():
        fixture.read()
    return fixture


@pytest.fixture
def chttpx_vars(request, chttpx_fixture):
    return chttpx_fixture.vars


@pytest.fixture
def chttpx_requests(request, chttpx_fixture):
    return chttpx_fixture.requests


@pytest.fixture
def chttpx_mock(chttpx_fixture, request, tmp_path):
    if (
        'httpx_mock' in request.fixturenames
        or request.config.getoption('--chttpx-live')
    ):
        yield
    else:
        if (
            not request.config.getoption('--chttpx-rewrite')
            and chttpx_fixture.path.exists()
        ):
            httpx_mock = request.getfixturevalue('httpx_mock')
            chttpx_fixture.mock(httpx_mock)

        test_name = request.node.nodeid.replace('/', '_')
        log_path = tmp_path / test_name
        cli2.configure(str(log_path))

        yield  # Test runs here

        if (
            request.config.getoption('--chttpx-rewrite')
            or not chttpx_fixture.path.exists()
        ):
            with log_path.open('r') as f:
                chttpx_fixture.requests = cli2.parse(f.read())

            chttpx_fixture.write()
