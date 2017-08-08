# -*- coding: utf-8 -*-

import os
import sys
import time
import platform

from datetime import datetime

from riseml.consts import IS_BUNDLE

COLOR_CODES = {
    # 'black': 30,     NOTE: We don't want that color!
    'red': 31,
    'green': 32,
    'yellow': 33,
    'blue': 34,
    'magenta': 35,
    'cyan': 36,
    'light gray': 37,
    'dark gray': 90,
    'light red': 91,
    'light green': 92,
    'light yellow': 93,
    'light blue': 94,
    'light magenta': 95,
    'light cyan': 96,
    'white': 97
}

colors = {}

COLORS_DISABLED = not sys.stdout.isatty()

def get_job_name(job):
    if job.root is None:
        if job.role == 'sequence':
            return "+ (%s)" % job.changeset.config_section
        elif job.role in ('deploy', 'train'):
            return "%s:run" % job.changeset.config_section
        else:
            return '%s (%s)' % (job.name, job.changeset.config_section)
    elif job.role in ('deploy', 'train'):
        return 'run'
    elif job.role == 'tensorboard':
        return 'tensorboard (service: %s)' % job.service_name 
    else:
        return job.name


def get_color_pairs():
    for name, code in COLOR_CODES.items():
        yield(name, str(code))
        yield('bold_' + name, str(code) + ';1')


for (name, ansi_code) in get_color_pairs():
    colors[name] = ansi_code


def ansi_sequence(code):
    return "\033[%sm" % code


def color_string(s, color=None, ansi_code=None):
    assert color is not None or ansi_code is not None, "You need to supply `color` or `ansi_code` param."
    assert not (color is not None and ansi_code is not None), "You need to supply either `color` or `ansi_code`"

    if COLORS_DISABLED:
        # return non-colored string if non-terminal output
        return s
    else:
        if color:
            ansi_code = colors[color]
        return "%s%s%s" % (ansi_sequence(ansi_code), s, ansi_sequence(0))


class TableElement():
    pass

class TableRowDelimiter(TableElement):
    def __init__(self, symbol):
        self.symbol = symbol
    def __str__(self):
        return 'TableRowDelimiter ({})'.format(self.symbol)


def print_table(header, rows, min_widths=None):
    n_columns = len(header)

    if not min_widths:
        widths = [5] * n_columns  # 5 is default width
    else:
        widths = list(min_widths)

    for row in rows:
        # skip table elements as non-data rows
        if isinstance(row, TableElement):
           continue

        row_items_count = len(row)
        assert row_items_count == n_columns, \
            "Column %s (columns: %d) must match" \
            " header's colums count: %d" % (str(row), row_items_count, n_columns)

        for i, cell in enumerate(row):
            item_len = len(cell) if not isinstance(cell, int) else len(str(cell))

            if item_len > widths[i]:
                widths[i] = item_len

    table_width = sum(widths) + n_columns - 1

    # see https://pyformat.info/
    # `Padding and aligning strings` block
    line_pattern = ''.join([
        '{:%s{widths[%s]}} ' % ('<', i)
        for i in range(n_columns)
    ])

    def bold(s): return color_string(s, ansi_code=1)
    def render_line(columns): return line_pattern.format(*columns, widths=widths)

    # print header
    print(bold(render_line(header)))

    # print rows
    for row in rows:
        if isinstance(row, TableRowDelimiter):
            print(row.symbol * table_width)
        else:
            print(render_line(row))


def get_since_str(timestamp):
    if not timestamp:
        return '-'
    now = int(time.time() * 1000)
    since_ms = now - timestamp
    days, since_ms = divmod(since_ms, 24 * 60 * 60 * 1000)
    hours, since_ms = divmod(since_ms, 60 * 60 * 1000)
    minutes, since_ms = divmod(since_ms, 60 * 1000)
    seconds, since_ms = divmod(since_ms, 1000)
    if days > 0:
        return "%s day(s)" % days
    elif hours > 0:
        return "%s hour(s)" % hours
    elif minutes > 0:
        return "%s minute(s)" % minutes
    elif seconds > 0:
        return "%s second(s)" % seconds
    else:
        return "just now"


def str_timestamp(timestamp):
    return datetime.utcfromtimestamp(int(timestamp)).strftime('%Y-%m-%dT%H:%M:%SZ')


def mb_to_gib(value):
    return "%.1f" % (float(value) * (10 ** 6) / (1024 ** 3))


def get_rsync_path():
    if IS_BUNDLE:
        return os.path.join(sys._MEIPASS, 'bin', 'rsync')
    else:
        return resolve_path('rsync')


def resolve_path(binary):
    paths = os.environ.get('PATH', '').split(os.pathsep)
    exts = ['']
    if platform.system() == 'Windows':
        path_exts = os.environ.get('PATHEXT', '.exe;.bat;.cmd').split(';')
        has_ext = os.path.splitext(binary)[1] in path_exts
        if not has_ext:
            exts = path_exts
    for path in paths:
        for ext in exts:
            loc = os.path.join(path, binary + ext)
            if os.path.isfile(loc):
                return loc


from riseml.client.rest import ApiException
from riseml.errors import handle_http_error


def call_api(api_fn):
    try:
        return api_fn()
    except ApiException as e:
        handle_http_error(e.body, e.status)