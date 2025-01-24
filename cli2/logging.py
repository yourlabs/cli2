import datetime
import logging.config
import os
import re
import sys
import structlog
from pathlib import Path

import cli2.display


class YAMLFormatter:
    def __init__(self, colors=True):
        self.colors = colors

    def __call__(self, key, value):
        value = cli2.display.yaml_dump(value)
        if not self.colors:
            return value
        return cli2.display.yaml_highlight(value)


def configure():
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'WARNING').upper()
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

    log_dir = Path(os.getenv("HOME")) / '.local/cli2/log'
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    file_name = f'{sys.argv[0].split("/")[-1]}-{ts}-{cmd}.log'
    file_path = log_dir / file_name
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
            'file': {
                'level': 'DEBUG',
                'class': 'logging.handlers.WatchedFileHandler',
                'formatter': 'plain',
                'filename': str(file_path),
            },
        },
        'loggers': {
            'cli2': {
                'handlers': ['default', 'file'],
                'level': 'DEBUG',
                'propagate': True,
            }
        }
    }

    if os.getenv('HTTP_DEBUG'):
        LOGGING['loggers'].update({
            key: {
                'handlers': ['default', 'file'],
                'level': 'DEBUG',
                'propagate': True,
            } for key in ('httpx', 'httpcore')
        })

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
