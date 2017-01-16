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
    build_commands = []
    build_include = None
    batch_commands = []
    service_commands = []
    service_input = None
    service_output = None
    service_demo = None


def parse_list(l):
    if l is None:
        return
    if isinstance(l, list):
        return l
    return [l]


def parse_one(record):
    return parse_list(record)[0]


def parse_text(text):
    config = Config()
    tmp = yaml.load(text)

    config.title = tmp.get('title')
    config.description = tmp.get('description')
    config.github_repo = tmp.get('github_repo')

    config.image = parse_one(tmp['image'])

    if tmp.get('build'):
        config.build_commands = parse_list(tmp['build']['commands']) or []
        if tmp['build'].get('options'):
            config.build_include = parse_list(tmp['build']['options'].get('include'))

    if tmp.get('batch'):
        config.batch_commands = parse_list(tmp['batch']['commands']) or []

    if tmp.get('service'):
        config.service_commands = parse_list(tmp['service']['commands']) or []
        config.service_input = tmp['service'].get('input')
        config.service_output = tmp['service'].get('output')
        if tmp['service'].get('options'):
            config.service_demo = tmp['service']['options'].get('demo')

    return config


def parse(f):
    return parse_text(f.read())


def parse_file(filename):
    with open(filename) as f:
        return parse(f)
