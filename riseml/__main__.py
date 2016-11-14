import os
import sys
import argparse
import subprocess

import requests

from riseml import DefaultApi, ApiClient


try:
    stdout = sys.stdout.buffer
except AttributeError:
    stdout = sys.stdout


scratch_url = os.environ.get('RISEML_SCRATCH_ENDPOINT', 'https://scratch.riseml.com')
api_url = os.environ.get('RISEML_API_ENDPOINT', 'https://api.riseml.com')


def get_repo_root(cwd=None):
    if cwd is None:
        cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, '.git')):
        return cwd
    elif cwd != '/':
        return get_repo_name(os.path.dirname(cwd))


def get_repo_name():
    return os.path.basename(get_repo_root())


def get_key(path=None):
    if path:
        loc = os.path.expanduser(filename)
        if os.path.exists(loc):
            with open(loc) as f:
                return f.read()
    else:
        for filename in ['id_rsa.pub', 'id_dsa.pub']:
            loc = os.path.expanduser(os.path.join('~', '.ssh', filename))
            if os.path.exists(loc):
                with open(loc) as f:
                    return f.read()


def get_user():
    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)
    user = client.get_user()[0]
    return user


def get_repository(name):
    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)
    for repository in client.get_repositories():
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
    client.delete_scratch(repository.id)


def handle_http_error(res):
    print('ERROR: %s (%d)' % (res.json()['message'], res.status_code))
    sys.exit(1)


def add_create_parser(subparsers):
    parser = subparsers.add_parser('create')
    def run(args):
        repository = create_repository(get_repo_name())
        print("repository created: %s (%s)" % (repository.name, repository.id))

    parser.set_defaults(run=run)


def add_ls_parser(subparsers):
    parser = subparsers.add_parser('ls')
    parser.add_argument('name', nargs='?', default='')
    def run(args):
        repository = get_repository(get_repo_name())
        res = requests.get('%s/%s/%s' % (scratch_url, repository.id, args.name))
        if res.status_code == 200 and res.headers['content-type'] == 'application/json':
            for entry in res.json():
                print(entry['name'])

    parser.set_defaults(run=run)


def add_cp_parser(subparsers):
    parser = subparsers.add_parser('cp')
    parser.add_argument('src')
    parser.add_argument('dst')
    def run(args):
        repository = get_repository(get_repo_name())
        res = requests.get('%s/%s/%s' % (scratch_url, repository.id, args.src), stream=True)
        if res.status_code == 200:
            with open(args.dst, 'wb') as f:
                for buf in res.iter_content(4096):
                    f.write(buf)

    parser.set_defaults(run=run)


def add_cat_parser(subparsers):
    parser = subparsers.add_parser('cat')
    parser.add_argument('name')
    def run(args):
        repository = get_repository(get_repo_name())
        res = requests.get('%s/%s/%s' % (scratch_url, repository.id, args.name), stream=True)
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
        print("%s (%s)" % (user.username, user.id))

    parser.set_defaults(run=run)


def add_logs_parser(subparsers):
    parser = subparsers.add_parser('logs')
    def run(args):
        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)
        job_id = client.get_jobs()[-1].id

        res = requests.get('%s/jobs/%s/logs' % (api_url, job_id),
            headers={'Authorization': os.environ.get('RISEML_APIKEY')},
            stream=True)

        if res.status_code == 200:
            for buf in res.iter_content(4096):
                stdout.write(buf)

    parser.set_defaults(run=run)


def add_push_parser(subparsers):
    parser = subparsers.add_parser('push')
    def run(args):
        proc = subprocess.Popen(['git', 'rev-parse', '--verify', 'HEAD'],
            cwd=get_repo_root(),
            stdout=subprocess.PIPE)
        revision = proc.stdout.read().strip()

        proc = subprocess.Popen(['/usr/bin/git', 'archive', '--format=tgz', 'HEAD'],
            cwd=get_repo_root(),
            stdout=subprocess.PIPE)

        res = requests.post('%s/changesets' % api_url,
            data={
                'revision': revision,
                'repository': get_repo_name(),
            },
            files={
                'changeset': proc.stdout,
            },
            headers={'Authorization': os.environ.get('RISEML_APIKEY')},
            stream=True)

        if res.status_code != 200:
            handle_http_error(res)
        else:
            for buf in res.iter_content(4096):
                stdout.write(buf)
                stdout.flush()

    parser.set_defaults(run=run)


def add_update_key_parser(subparsers):
    parser = subparsers.add_parser('update-key')
    parser.add_argument('path', nargs='?', default='')
    def run(args):
        public_key = get_key(args.path)
        if not public_key:
            print("no key found")
            sys.exit(1)

        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)
        user = client.update_user(ssh_key=public_key)[0]
        print("public key for %s (%s)" % (user.username, user.fingerprint))

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
    add_logs_parser(subparsers)
    add_push_parser(subparsers)
    add_update_key_parser(subparsers)
    return parser


parser = get_parser()
args = parser.parse_args(sys.argv[1:])
if hasattr(args, 'run'):
    args.run(args)
else:
    parser.print_usage()
