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
import io
import structlog
import yaml
from pathlib import Path

from cli2.traceback import TracebackFormatter
from cli2.theme import theme
import cli2.display


COLOR_ENABLED = cli2.display.color_enabled()


class YAMLFormatter:
    def __init__(self, colors=True):
        self.colors = colors

    def __call__(self, key, value):
        value = cli2.display.yaml_dump(value)
        if self.colors:
            value = cli2.display.yaml_highlight(value)
        return '\n' + value.strip() + '\n'


_NOTHING = structlog.dev._NOTHING


class ConsoleRenderer(structlog.dev.ConsoleRenderer):
    def __init__(self, *args, **kwargs):
        if kwargs.get('colors', False):
            kwargs['level_styles'] = dict(
                debug=str(theme.gray),
                info=str(theme.green),
                warning=str(theme.orange),
                error=str(theme.red),
                critical=str(theme.pink),
                exception=str(theme.mauve),
            )

        super().__init__(*args, **kwargs)
        self._columns.append(
            structlog.dev.Column(
                'json',
                YAMLFormatter(colors=self.colors),
            ),
        )
    def _configure_columns(self) -> None:
        super()._configure_columns()
        if self.colors:
            self._default_column_formatter.key_style = str(theme.orange)
            self._default_column_formatter.value_style = str(theme.green)

    def __call__(self, logger, name, event_dict):
        """ Override to display JSON column last """
        stack = event_dict.pop("stack", None)
        exc = event_dict.pop("exception", None)
        exc_info = event_dict.pop("exc_info", None)

        self.columns[3].formatter.width = 0
        kvs = [
            col.formatter(col.key, val)
            for col in self.columns
            if col.key != 'json'
            and (val := event_dict.pop(col.key, _NOTHING)) is not _NOTHING
            # added the following line:
        ] + [
            self._default_column_formatter(key, event_dict[key])
            for key in (sorted(event_dict) if self._sort_keys else event_dict)
            if key != 'json'
        ] + [
            # added all this list
            col.formatter(col.key, val)
            for col in self.columns
            if col.key == 'json'
            and (val := event_dict.pop(col.key, _NOTHING)) is not _NOTHING
        ]

        sio = io.StringIO()
        sio.write((" ".join(kv for kv in kvs if kv)).rstrip(" "))

        if stack is not None:
            sio.write("\n" + stack)
            if exc_info or exc is not None:
                sio.write("\n\n" + "=" * 79 + "\n")

        exc_info = structlog.processors._figure_out_exc_info(exc_info)
        if exc_info:
            self._exception_formatter(sio, exc_info)
        elif exc is not None:
            if self._exception_formatter is not plain_traceback:
                warnings.warn(
                    "Remove `format_exc_info` from your processor chain "
                    "if you want pretty exceptions.",
                    stacklevel=2,
                )

            sio.write("\n" + exc)

        return sio.getvalue()


def cli2_traceback(sio, exc_info):
    exc_type, exc_value, exc_traceback = exc_info
    formatter = TracebackFormatter()
    formatter.parse(exc_type, exc_value, exc_traceback)
    sio.write('\n' + '\n'.join(formatter.output))


def configure(log_file=None):
    """
    Configure logging.

    :param log_file: override for :envvar:`LOG_FILE`.
    """
    from cli2.configuration import cfg
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'WARNING').upper()
    if log_file is None:
        log_file = os.getenv('LOG_FILE', 'auto')

    if os.getenv('DEBUG'):
        LOG_LEVEL = 'DEBUG'

    pre_chain = [
        # add log level and timestamp to event_dict
        structlog.stdlib.add_log_level,
        # Add extra attributes of Logrecord objects to the event dictionnary so
        # that values in the extra parameters of log methods pass through to
        # log output
        structlog.stdlib.ExtraAdder(),
    ]

    if 'NO_TIMESTAMPER' not in os.environ:
        timestamper = structlog.processors.TimeStamper(fmt='%Y-%m-%d %H:%M:%S')
        pre_chain.append(timestamper)

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

    kwargs = dict()
    if not bool(cfg['CLI2_TRACEBACK_DISABLE']):
        kwargs['exception_formatter'] = cli2_traceback

    from structlog.processors import StackInfoRenderer, TimeStamper, add_log_level
    from structlog.contextvars import merge_contextvars
    from structlog.dev import _has_colors, set_exc_info
    colors = (
        os.environ.get("NO_COLOR", "") == ""
        and (
            os.environ.get("FORCE_COLOR", "") != ""
            or (
                _has_colors
                and sys.stdout is not None
                and hasattr(sys.stdout, "isatty")
                and sys.stdout.isatty()
            )
        )
    )
    def move_json_to_end(_, __, event_dict):
        # Pull json out if present, then put it back at the very end
        json_value = event_dict.pop("json", None)
        if json_value is not None:
            event_dict["json"] = json_value
        return event_dict

    def processors(disable_color=False):
        return [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            merge_contextvars,
            add_log_level,
            StackInfoRenderer(),
            set_exc_info,
            TimeStamper(fmt="%Y-%m-%d %H:%M:%S", utc=False),
            ConsoleRenderer(
                colors=colors and not disable_color,
            ),
        ]

    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'plain': {
                'foreign_pre_chain': pre_chain,
                '()': structlog.stdlib.ProcessorFormatter,
                'processors': processors(True),
            },
            'colored': {
                'foreign_pre_chain': pre_chain,
                '()': structlog.stdlib.ProcessorFormatter,
                'processors': processors(),
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

    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
    ]

    if 'NO_TIMESTAMPER' not in os.environ:
        processors.append(timestamper)

    processors += [
        structlog.processors.StackInfoRenderer(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]

    structlog.configure(
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
        processors=processors,
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

            entries.append(data)
            yaml_lines = []
        else:
            yaml_lines.append(line)
    return entries


class LazyProxy:
    def __init__(self):
        self.obj = None

    def __getattr__(self, key):
        try:
            return getattr(self.obj, key)
        except AttributeError:
            self.obj = self.obj_factory()
            return getattr(self.obj, key)

    def obj_factory(self):
        configure()
        return structlog.get_logger('cli2')

log = LazyProxy()
