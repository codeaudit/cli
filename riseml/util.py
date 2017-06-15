

COLOR_NAMES = [
    'grey',
    'red',
    'green',
    'yellow',
    'blue',
    'magenta',
    'cyan',
    'white'
]

colors = {}


def get_color_pairs():
    for i, name in enumerate(COLOR_NAMES):
        yield(name, str(30 + i))
        yield('bold_' + name, str(30 + i) + ';1')


for (name, ansi_code) in get_color_pairs():
    colors[name] = ansi_code


def ansi_sequence(code):
    return "\033[%sm" % code


def color_string(color, s):
    ansi_code = colors[color]
    return "%s%s%s" % (ansi_sequence(ansi_code), s, ansi_sequence(0))
