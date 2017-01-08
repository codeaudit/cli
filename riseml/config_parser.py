import sys
import os
import subprocess
import contextlib

import yaml
import requests


class ConfigException(Exception): pass


@contextlib.contextmanager
def chdir(new_dir):
    old_dir = os.getcwd()
    try:
        os.chdir(new_dir)
        sys.path.insert(0, new_dir)
        yield
    finally:
        del sys.path[0]
        os.chdir(old_dir)


class Config(object):
    image = None
    commands = None
    template = None


def parse_text(text):
    config = Config()
    tmp = yaml.load(text)
    if not 'image' in tmp:
        raise ConfigException(u'missing key: image')
    elif not 'script' in tmp:
        raise ConfigException(u'missing key: script')

    if isinstance(tmp['image'], list):
        if len(tmp['image']) > 1:
            raise ConfigException(u"you can only specify a single image")
        config.image = tmp['image'][0]
    else:
        config.image = tmp['image']

    if isinstance(tmp['script'], list):
        config.commands = tmp['script']
    else:
        config.commands = [tmp['script']]

    if 'template' in tmp:
        config.template = tmp['template']

    return config


def parse(f):
    return parse_text(f.read())


def parse_file(filename):
    with open(filename) as f:
        return parse(f)
