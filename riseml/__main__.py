import json
import os
import sys
import argparse
import subprocess

import requests

import riseml
from riseml import DefaultApi, AdminApi, ApiClient


try:
    stdout = sys.stdout.buffer
except AttributeError:
    stdout = sys.stdout


try:
    from subprocess import dev_null  # py3
except ImportError:
    import os
    dev_null = open(os.devnull, 'wb')


api_url = os.environ.get('RISEML_API_ENDPOINT', 'https://api.riseml.com')
git_url = os.environ.get('RISEML_GIT_ENDPOINT', 'git@git.riseml.com')


def get_repo_root(cwd=None):
    if cwd is None:
        cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, '.git')):
        return cwd
    elif cwd != '/':
        return get_repo_root(os.path.dirname(cwd))


def get_repo_name():
    repo_root = get_repo_root()
    if not repo_root:
        handle_error("no git repository found")
    return os.path.basename(repo_root)


def get_key(path=None):
    if path:
        loc = os.path.expanduser(filename)
        if os.path.exists(loc):
            with open(loc) as f:
                return (loc, f.read())
    else:
        for filename in ['id_rsa.pub', 'id_dsa.pub']:
            loc = os.path.expanduser(os.path.join('~', '.ssh', filename))
            if os.path.exists(loc):
                with open(loc) as f:
                    return (loc, f.read())


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
    handle_error("repository not found: %s" % name)

def create_repository(name):
    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)
    return client.create_repository(name)[0]


def handle_error(message, status_code=None):
    if status_code:
        print('ERROR: %s (%d)' % (message, status_code))
    else:
        print('ERROR: %s' % message)
    sys.exit(1)


def handle_http_error(res):
    handle_error(res.json()['message'], res.status_code)


def add_create_parser(subparsers):
    parser = subparsers.add_parser('create', help="create repository")
    def run(args):
        repository = create_repository(get_repo_name())
        print("repository created: %s (%s)" % (repository.name, repository.id))

    parser.set_defaults(run=run)


def add_register_parser(subparsers):
    parser = subparsers.add_parser('register', help="register user (only admin)")
    parser.add_argument('--username', help="a person's username", required=True)
    parser.add_argument('--email', help="a person's email", required=True)
    def run(args):
        api_client = ApiClient(host=api_url)
        client = AdminApi(api_client)
        user = None
        try:
            user = client.create_user(username=args.username, email=args.email)[0]
        except riseml.rest.ApiException as e:
            body = json.loads(e.body)
            handle_error(body['message'], e.status)
        print(user)

    parser.set_defaults(run=run)


def add_ls_parser(subparsers):
    parser = subparsers.add_parser('ls', help="list directory from scratch")
    parser.add_argument('file', help="scratch file path", nargs='?', default='')
    def run(args):
        repo_name = get_repo_name()
        repository = get_repository(repo_name)

        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)
        entries = client.get_scratch_meta(repository.id, args.file)
        for entry in entries:
            if entry.is_dir:
                print(" " * 11 + " %s" % (entry.name))
            else:
                print("%11d %s" % (entry.size, entry.name))

    parser.set_defaults(run=run)


def add_cp_parser(subparsers):
    parser = subparsers.add_parser('cp', help="cp file from scratch")
    parser.add_argument('src', help="scratch file path")
    parser.add_argument('dst', help="local file path")
    def run(args):
        repository = get_repository(get_repo_name())
        res = requests.get('%s/scratches/%s/%s' % (api_url, repository.id, args.src),
            headers={'Authorization': os.environ.get('RISEML_APIKEY')},
            stream=True)
        if res.status_code == 200:
            with open(args.dst, 'wb') as f:
                for buf in res.iter_content(4096):
                    f.write(buf)

    parser.set_defaults(run=run)


def add_cat_parser(subparsers):
    parser = subparsers.add_parser('cat', help="print file contents from scratch")
    parser.add_argument('file', help="scratch file path")
    def run(args):
        repository = get_repository(get_repo_name())
        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)
        entry = client.get_scratch_object(repository.id, args.file)

        res = requests.get('%s/scratches/%s/%s' % (api_url, repository.id, args.file),
            headers={'Authorization': os.environ.get('RISEML_APIKEY')},
            stream=True)
        if res.status_code == 200:
            for buf in res.iter_content(4096):
                stdout.write(buf)

    parser.set_defaults(run=run)


def add_clean_parser(subparsers):
    parser = subparsers.add_parser('clean', help="remove all data from scratch")
    parser.add_argument('file', help="scratch file path", nargs='?', default='')
    def run(args):
        repository = get_repository(get_repo_name())
        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)
        client.delete_scratch_object(repository.id, args.file)

    parser.set_defaults(run=run)


def add_whoami_parser(subparsers):
    parser = subparsers.add_parser('whoami', help="show currently logged in user")
    def run(args):
        user = get_user()
        print("%s (%s)" % (user.username, user.id))

    parser.set_defaults(run=run)


def add_logs_parser(subparsers):
    parser = subparsers.add_parser('logs', help="show logs")
    parser.add_argument('job', help="job identifier (optional)", nargs='?', default='')
    def run(args):
        job_id = None
        if args.job:
            job_id = args.job
        else:
            api_client = ApiClient(host=api_url)
            client = DefaultApi(api_client)
            repository = get_repository(get_repo_name())
            job_id = client.get_repository_jobs(repository.id)[-1].id

        res = requests.get('%s/jobs/%s/logs' % (api_url, job_id),
            headers={'Authorization': os.environ.get('RISEML_APIKEY')},
            stream=True)

        if res.status_code == 200:
            print("logs for job %s" % job_id)
            for buf in res.iter_content(4096):
                stdout.write(buf)
                stdout.flush()

    parser.set_defaults(run=run)


def add_kill_parser(subparsers):
    parser = subparsers.add_parser('kill', help="kill job")
    parser.add_argument('job', help="job identifier")
    def run(args):
        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)
        try:
            job = client.kill_job(args.job)[0]
        except riseml.rest.ApiException as e:
            body = json.loads(e.body)
            handle_error(body['message'], e.status)
        print("job killed (%s)" % (job.id))

    parser.set_defaults(run=run)


def add_push_parser(subparsers):
    parser = subparsers.add_parser('push', help="run new job")
    def run(args):
        repository = get_repository(get_repo_name())

        proc = subprocess.Popen(['git', 'rev-parse', '--verify', 'HEAD'],
            cwd=get_repo_root(),
            stdout=subprocess.PIPE,
            stderr=dev_null)
        revision = proc.stdout.read().strip()

        proc = subprocess.Popen(['/usr/bin/git', 'archive', '--format=tgz', 'HEAD'],
            cwd=get_repo_root(),
            stdout=subprocess.PIPE,
            stderr=dev_null)

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


def add_init_ssh_parser(subparsers):
    parser = subparsers.add_parser('init-ssh', help="initialize setup for push via git")
    parser.add_argument('ssh_key', help="path to ssh key (default: ~/.ssh/id_(rsa|dsa).pub",
        metavar='ssh-key', nargs='?', default='')
    def run(args):
        public_key_path, public_key = get_key(args.ssh_key)
        if not public_key:
            print("no key found")
            sys.exit(1)

        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)

        try:
            user = client.update_user(ssh_key=public_key)[0]
        except riseml.rest.ApiException as e:
            body = json.loads(e.body)
            handle_error(body['message'], e.status)

        proc = subprocess.Popen(['git', 'remote', 'remove', 'riseml'],
            stdout=dev_null,
            stderr=dev_null,
            cwd=get_repo_root())

        repo_url = git_url + ':' + get_repo_name()
        proc = subprocess.Popen(['git', 'remote', 'add', 'riseml', repo_url],
            stdout=dev_null,
            stderr=dev_null,
            cwd=get_repo_root())

        print("added public key %s for %s (%s)" % (public_key_path, user.username, user.fingerprint))
        print("added riseml remote, use: git push --set-upstream riseml master")

    parser.set_defaults(run=run)


def add_ps_parser(subparsers):
    parser = subparsers.add_parser('ps', help="show jobs")
    parser.add_argument('-a', help="show all jobs",
        action='store_const', const=True)
    def run(args):
        def filter_jobs(jobs):
            res = []
            for job in jobs:
                if args.a:
                    status = job.status
                    if job.reason:
                        status += ': ' + job.reason
                    res.append("%s (%s)" % (job.id, status))
                else:
                    if job.status == 'TASK_RUNNING':
                        res.append(job.id)
            return res

        repo_name = get_repo_name()

        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)
        all_jobs = client.get_jobs()

        if repo_name:
            repository = get_repository(repo_name)
            my_jobs = client.get_repository_jobs(repository.id)
            filtered_jobs = filter_jobs(my_jobs)
            if filtered_jobs:
                print("%s jobs" % repo_name)
                print("\n".join(filtered_jobs))

        filtered_jobs = filter_jobs([job for job in all_jobs if job not in my_jobs])
        if filtered_jobs:
            print("other jobs")
            print("\n".join(filtered_jobs))

    parser.set_defaults(run=run)


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', help="show endpoints",
        action='store_const', const=True)

    subparsers = parser.add_subparsers()

    # user ops
    add_register_parser(subparsers)
    add_whoami_parser(subparsers)
    add_init_ssh_parser(subparsers)

    # worklow ops
    add_create_parser(subparsers)
    add_push_parser(subparsers)
    add_logs_parser(subparsers)
    add_kill_parser(subparsers)

    # scratch ops
    add_ps_parser(subparsers)
    add_ls_parser(subparsers)
    add_cp_parser(subparsers)
    add_cat_parser(subparsers)
    add_clean_parser(subparsers)

    return parser


parser = get_parser()
args = parser.parse_args(sys.argv[1:])
if args.v:
    print('RISEML_API_ENDPOINT: %s' % api_url)
    print('RISEML_GIT_ENDPOINT: %s' % git_url)
if hasattr(args, 'run'):
    args.run(args)
else:
    parser.print_usage()
