# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import re

COLORS_DISABLED = not sys.stdout.isatty()
colors = {}

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


def bold(s): return color_string(s, ansi_code=1)


def get_color_pairs():
    for name, code in COLOR_CODES.items():
        yield(name, str(code))
        yield('bold_' + name, str(code) + ';1')


for (name, ansi_code) in get_color_pairs():
    colors[name] = ansi_code


def ansi_sequence(code):
    return "\033[%sm" % code


# from https://github.com/jonathaneunice/colors/blob/master/colors/colors.py
def strip_color(s):
    return re.sub('\x1b\\[(K|.*?m)', '', s)


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