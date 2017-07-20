import time

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


def color_string(color, s):
    ansi_code = colors[color]
    return "%s%s%s" % (ansi_sequence(ansi_code), s, ansi_sequence(0))

def format_header(columns, widths=(4, 10, 9, 8)):
    def bold(s):
        return '\033[1m{}\033[0m'.format(s)
    header = ''
    for i, w in enumerate(widths):
        header += '{:%s{widths[%s]}} ' % ('<', i)
    return bold(header.format(*columns, widths=widths))

def format_line(columns, widths=(4, 10, 9, 8)):
    line = '{:>{widths[0]}} {:<{widths[1]}} {:>{widths[2]}} {:<{widths[3]}}'
    line = ''
    for i, w in enumerate(widths):
        line += '{:%s{widths[%s]}} ' % ('<', i)
    return line.format(*columns, widths=widths)

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
