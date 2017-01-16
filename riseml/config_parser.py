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
    title = None
    description = None
    github_repo = None
    image = None
    build_commands = None
    build_include = None
    batch_commands = None
    service_commands = None
    service_input = None
    service_output = None
    service_demo = None


def parse_list(l):
    if isinstance(l, list):
        return l
    return l


def parse_text(text):
    config = Config()
    tmp = yaml.load(text)
    if not 'image' in tmp:
        raise ConfigException(u'missing key: image')

    config.title = tmp['title']
    config.description = tmp['description']
    config.github_repo = tmp['github_repo']
    config.image = tmp['image']
    config.build_commands = parse_list(tmp['build']['commands'])
    config.build_include = parse_list(tmp['build']['options']['include'])
    config.batch_commands = parse_list(tmp['batch']['commands'])
    config.service_commands = parse_list(tmp['service']['commands'])
    config.service_input = tmp['service']['input']
    config.service_output = tmp['service']['output']
    config.service_demo = tmp['service']['options']['demo']
    return config


def parse(f):
    return parse_text(f.read())


def parse_file(filename):
    with open(filename) as f:
        return parse(f)
