# -*- coding: utf-8 -*-
import json
import re
import os
import sys
import time
import argparse
import subprocess
import platform
import webbrowser
import requests
import websocket
import yaml
from datetime import datetime

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from . import util

from riseml.client import DefaultApi, AdminApi, ScratchEntry, ApiClient
from riseml.client.rest import ApiException
from riseml.config_parser import parse_file


endpoint_url = os.environ.get('RISEML_ENDPOINT', 'http://127.0.0.1:8080')
sync_url = os.environ.get('RISEML_SYNC_ENDPOINT', 'rsync://192.168.99.100:31876/sync')
user_url = os.environ.get('RISEML_USER_ENDPOINT', 'https://%s.riseml.io')
api_url = endpoint_url + '/api'
git_url = endpoint_url + '/git'
stream_url = "ws://%s/stream" % urlparse(endpoint_url).netloc

ANSI_ESCAPE_REGEX = re.compile(r'\x1b[^m]*m')

# avoid using ~.netrc
class NoAuth(object):
    def __call__(self, request):
        return request


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


def get_project_root(cwd=None):
    if cwd is None:
        cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, 'riseml.yml')):
        return cwd
    elif cwd != '/':
        return get_project_root(os.path.dirname(cwd))


def get_project_name():
    project_root = get_project_root()
    if not project_root:
        handle_error("no riseml project found")
    config = parse_file(os.path.join(project_root, 'riseml.yml'))
    return config.project


def get_user():
    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)
    user = client.get_user()[0]
    return user


def get_project(name):
    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)
    for project in client.get_repositories():
        if project.name == name:
            return project
    handle_error("project not found: %s" % name)


def handle_error(message, status_code=None):
    if status_code:
        print('ERROR: %s (%d)' % (message, status_code))
    else:
        print('ERROR: %s' % message)
    sys.exit(1)


def handle_http_error(res):
    handle_error(res.json()['message'], res.status_code)


def load_config(config_file, config_section):
    if not os.path.exists(config_file):
        handle_error("%s does not exist" % config_file)
    with open(config_file, 'r') as f:
        config = yaml.load(f.read())
        if config_section not in config:
            handle_error("config doesn't contain section for %s" % config_section)
        return config[config_section]


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', help="show endpoints",
                        action='store_const', const=True)

    subparsers = parser.add_subparsers()

    # user ops
    add_register_parser(subparsers)
    add_whoami_parser(subparsers)

    # clusterinfo ops
    add_cluster_parser(subparsers)

    # worklow ops
    add_train_parser(subparsers)
    add_exec_parser(subparsers)
    add_deploy_parser(subparsers)
    add_logs_parser(subparsers)
    add_kill_parser(subparsers)
    add_status_parser(subparsers)

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args(sys.argv[1:])
    if args.v:
        print('api_url: %s' % api_url)
        print('stream_url: %s' % stream_url)
        #print('RISEML_SCRATCH_ENDPOINT: %s' % scratch_url)
        print('git_url: %s' % git_url)
        print('user_url: %s' % user_url)
    if hasattr(args, 'run'):
        args.run(args)
    else:
        parser.print_usage()


if __name__ == '__main__':
    main()
