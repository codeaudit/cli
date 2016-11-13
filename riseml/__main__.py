import os
import sys
import argparse

import requests

from riseml import DefaultApi, ApiClient


try:
    stdout = sys.stdout.buffer
except AttributeError:
    stdout = sys.stdout


scratch_url = 'https://scratch.riseml.com'
# api_url = 'http://api.riseml.com:5000'
api_url = 'http://localhost:5000'


def get_repo_name(cwd=None):
    if cwd is None:
        cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, '.git')):
        return os.path.basename(cwd)
    elif cwd != '/':
        return get_repo_name(os.path.dirname(cwd))


def get_user():
    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)
    user = client.get_user()[0]
    return user


def get_repository(name):
    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)
    for repository in client.get_repositories():
        print(repository.name)
        if repository.name == name:
            return repository


def create_repository(name):
    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)
    return client.create_repository(name)[0]


def clean_scratch():
    repository = get_repository(get_repo_name())
    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)
    return client.delete_scratch(repository.id)[0]


def add_create_parser(subparsers):
    parser = subparsers.add_parser('create')
    def run(args):
        repository = create_repository(get_repo_name())
        print("repository created: %s" % repository.name)

    parser.set_defaults(run=run)


def add_ls_parser(subparsers):
    parser = subparsers.add_parser('ls')
    parser.add_argument('name', nargs='?', default='')
    def run(args):
        # name = get_repo_name()
        res = requests.get('%s/%s/%s' % (scratch_url, get_user().id, args.name))
        if res.status_code == 200 and res.headers['content-type'] == 'application/json':
            print("\n".join([entry['name'] for entry in res.json()]))

    parser.set_defaults(run=run)


def add_cp_parser(subparsers):
    parser = subparsers.add_parser('cp')
    parser.add_argument('src')
    parser.add_argument('dst')
    def run(args):
        # name = get_repo_name()
        res = requests.get('%s/%s/%s' % (scratch_url, get_user().id, args.src), stream=True)
        if res.status_code == 200:
            with open(args.dst, 'wb') as f:
                for buf in res.iter_content(4096):
                    f.write(buf)

    parser.set_defaults(run=run)


def add_cat_parser(subparsers):
    parser = subparsers.add_parser('cat')
    parser.add_argument('name')
    def run(args):
        # name = get_repo_name()
        res = requests.get('%s/%s/%s' % (scratch_url, get_user().id, args.name), stream=True)
        if res.status_code == 200:
            for buf in res.iter_content(4096):
                stdout.write(buf)

    parser.set_defaults(run=run)


def add_clean_parser(subparsers):
    parser = subparsers.add_parser('clean')
    def run(args):
        clean_scratch()

    parser.set_defaults(run=run)


def add_whoami_parser(subparsers):
    parser = subparsers.add_parser('whoami')
    def run(args):
        user = get_user()
        print(user.username, user.id)

    parser.set_defaults(run=run)


def get_parser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    add_create_parser(subparsers)
    add_ls_parser(subparsers)
    add_cp_parser(subparsers)
    add_cat_parser(subparsers)
    add_clean_parser(subparsers)
    add_whoami_parser(subparsers)
    return parser


parser = get_parser()
args = parser.parse_args(sys.argv[1:])
if hasattr(args, 'run'):
    args.run(args)
else:
    parser.print_usage()
