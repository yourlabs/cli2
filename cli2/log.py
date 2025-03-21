"""
Structlog based beautiful logging.

This configuration offers YAML rendering for the ``json`` key in every log
calls.

.. code-block:: python

    import cli2

    cli2.log.warn("something happened", custom=key, json=will_be_prettyfied)

In general, you'll want to use want to use:

- ``log.debug()``: to indicate that something is going to happen, or a
  request is being sent
- ``log.info()``: to indicate that something **has** happened, or a response
  was received
- ``log.warn()``: something hasn't happened as expected, but your program
  can recover from that (ie. retrying a connection)
- ``log.error()``: your program couldn't perform some function
- ``log.critical()``: your program may not be able to continue running

Anyway, it's structlog so you can also create bound loggers that will carry on
the given parameters:

.. code-block:: python

    import cli2
    log = cli2.log.bind(some='var')
    log.warn('hello')  # will log with some=var

Log level is set to warning by default, configurable over environment
variables.

.. envvar:: LOG_LEVEL

    Setting this to ``INFO``, ``DEBUG``, or any other log level is safe.

.. envvar:: LOG_FILE

    Path to log file to use, with a couple of special values:

    - if ``LOG_FILE=auto``, then a path will be calculated in
      ``~/.local/cli2/log``,
    - if ``LOG_FILE=none``, then there will be no file logging.

    Default: ``auto``

.. envvar:: DEBUG

    Setting this will set :envvar:`LOG_LEVEL` to `DEBUG`, but also activate
    otherwise hidden outputs, such as, in cli2.client: long pagination outputs,
    secret/masked variables.
    This variable is designed to **never** be enabled in automated runs, to
    avoid leaking way to much information in say Ansible Tower and stuff like
    that.
    But if you're debugging manually, you will surely need that at some point.
"""

import datetime
import logging.config
import os
import re
import sys
import structlog
import yaml
from pathlib import Path

import cli2.display


class YAMLFormatter:
    def __init__(self, colors=True):
        self.colors = colors

    def __call__(self, key, value):
        value = cli2.display.yaml_dump(value)
        if self.colors:
            value = cli2.display.yaml_highlight(value)
        return '\n' + value


def configure(log_file=None):
    """
    Configure logging.

    :param log_file: override for :envvar:`LOG_FILE`.
    """
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'WARNING').upper()
    if log_file is None:
        log_file = os.getenv('LOG_FILE', 'auto')

    if os.getenv('DEBUG'):
        LOG_LEVEL = 'DEBUG'

    timestamper = structlog.processors.TimeStamper(fmt='%Y-%m-%d %H:%M:%S')
    pre_chain = [
        # add log level and timestamp to event_dict
        structlog.stdlib.add_log_level,
        # Add extra attributes of Logrecord objects to the event dictionnary so
        # that values in the extra parameters of log methods pass through to
        # log output
        structlog.stdlib.ExtraAdder(),
        timestamper,
    ]

    cmd = '_'.join([
        re.sub('[^0-9a-zA-Z]+', '_', arg.split('/')[-1])
        for arg in sys.argv
    ])[:155]

    if log_file == 'auto':
        log_dir = Path(os.getenv("HOME")) / '.local/cli2/log'
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        file_name = f'{sys.argv[0].split("/")[-1]}-{ts}-{cmd}.log'
        log_file = log_dir / file_name
    elif log_file == 'none' or not log_file:
        log_file = None
    else:
        log_file = Path(log_file)

    handlers = ['default']
    if log_file:
        handlers.append('file')

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'plain': {
                'foreign_pre_chain': pre_chain,
                '()': structlog.stdlib.ProcessorFormatter,
                'processors': [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(
                        columns=[
                            structlog.dev.Column(
                                'json',
                                YAMLFormatter(colors=False),
                            ),
                            structlog.dev.Column(
                                '',
                                structlog.dev.KeyValueColumnFormatter(
                                    key_style="",
                                    value_style="",
                                    reset_style="",
                                    value_repr=str,
                                ),
                            )
                        ],
                    )
                ],
            },
            'colored': {
                'foreign_pre_chain': pre_chain,
                '()': structlog.stdlib.ProcessorFormatter,
                'processors': [
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.dev.ConsoleRenderer(
                        columns=[
                            structlog.dev.Column(
                                '',
                                structlog.dev.KeyValueColumnFormatter(
                                    key_style=structlog.dev.CYAN,
                                    value_style=structlog.dev.MAGENTA,
                                    reset_style=structlog.dev.RESET_ALL,
                                    value_repr=str,
                                ),
                            ),
                            structlog.dev.Column(
                                'json',
                                YAMLFormatter(colors=True),
                            ),
                        ],
                    )
                ]
            },
        },
        'handlers': {
            'default': {
                'level': LOG_LEVEL,
                'class': 'logging.StreamHandler',
                'formatter': 'colored',
            },
        },
        'loggers': {
            'cli2': {
                'handlers': handlers,
                'level': 'DEBUG',
                'propagate': True,
            }
        }
    }

    if os.getenv('HTTP_DEBUG'):
        LOGGING['loggers'].update({
            key: {
                'handlers': handlers,
                'level': 'DEBUG',
                'propagate': True,
            } for key in ('httpx', 'httpcore')
        })

    if log_file:
        LOGGING['handlers']['file'] = {
            'level': 'DEBUG',
            'class': 'logging.handlers.WatchedFileHandler',
            'formatter': 'plain',
            'filename': str(log_file),
        }

    logging.config.dictConfig(LOGGING)

    structlog.configure(
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
    )


def parse(data):
    """
    Parse log file data into a list of entries.

    :param data: Contents of a log file.
    """
    yaml_lines = []
    entries = []
    for line in data.split('\n'):
        if 'event=' in line:
            data = {}
            for token in line.strip().split():
                if match := re.match('^(\\w+)=(.*)', token):
                    key = match.group(1)
                    data[key] = match.group(2)
                else:
                    data[key] += ' ' + token

            if yaml_lines:
                data['json'] = yaml.safe_load('\n'.join(yaml_lines))

            if data['event'] == 'request':
                entries.append(dict(request=data))
            elif data['event'] == 'response':
                entries[-1]['response'] = data
            else:
                entries.append(data)

            yaml_lines = []
        else:
            yaml_lines.append(line)
    return entries


configure()
log = structlog.get_logger('cli2')
