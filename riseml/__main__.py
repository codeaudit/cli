import json
import os
import sys
import argparse
import subprocess
import platform
import webbrowser
import re
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

import requests

from riseml.client import DefaultApi, AdminApi, ScratchApi, ApiClient
from riseml.client.rest import ApiException

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
scratch_url = os.environ.get('RISEML_SCRATCH_ENDPOINT', 'https://scratch.riseml.com:8443')
git_url = os.environ.get('RISEML_GIT_ENDPOINT', 'https://git.riseml.com')
user_url = os.environ.get('RISEML_USER_ENDPOINT', 'https://%s.riseml.io')


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
            user = client.update_or_create_user(username=args.username, email=args.email)[0]
        except ApiException as e:
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

        api_client = ApiClient(host=scratch_url)
        client = ScratchApi(api_client)
        entries = client.get_scratch_meta(repository.id, args.file)
        for entry in entries:
            if entry.is_dir:
                print(" " * 11 + " %s" % (entry.name))
            else:
                print("%11d %s" % (entry.size, entry.name))

    parser.set_defaults(run=run)


def add_cp_parser(subparsers):
    parser = subparsers.add_parser('cp', help="cp file from scratch")
    parser.add_argument('src', help="local or scratch file path")
    parser.add_argument('dst', help="local or scratch file path")
    def run(args):
        repository = get_repository(get_repo_name())
        local_prefix = ['~', '/', '.']

        # upload
        if args.src[0] in local_prefix and args.dst[0] not in local_prefix:
            res = requests.put('%s/scratches/%s/%s' % (scratch_url, repository.id, args.dst),
                headers={'Authorization': os.environ.get('RISEML_APIKEY')},
                auth=NoAuth(),
                files={'file': open(args.src, 'rb')})
            if res.status_code != 200:
                handle_http_error(res)

        # download
        elif args.src[0] not in local_prefix and args.dst[0] in local_prefix:
            res = requests.get('%s/scratches/%s/%s' % (scratch_url, repository.id, args.src),
                headers={'Authorization': os.environ.get('RISEML_APIKEY')},
                auth=NoAuth(),
                stream=True)
            if res.status_code != 200:
                handle_http_error(res)

            with open(args.dst, 'wb') as f:
                for buf in res.iter_content(4096):
                    f.write(buf)
        else:
            handle_error("copy operation not supported")

    parser.set_defaults(run=run)


def add_cat_parser(subparsers):
    parser = subparsers.add_parser('cat', help="print file contents from scratch")
    parser.add_argument('file', help="scratch file path")
    def run(args):
        repository = get_repository(get_repo_name())
        res = requests.get('%s/scratches/%s/%s' % (scratch_url, repository.id, args.file),
            headers={'Authorization': os.environ.get('RISEML_APIKEY')},
            auth=NoAuth(),
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
        api_client = ApiClient(host=scratch_url)
        client = ScratchApi(api_client)
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
    parser.add_argument('job', help="job identifier (optional)", nargs='?')
    def run(args):
        job_id = None
        if args.job:
            job_id = args.job
        else:
            api_client = ApiClient(host=api_url)
            client = DefaultApi(api_client)
            repository = get_repository(get_repo_name())
            jobs = client.get_repository_jobs(repository.id)
            if not jobs:
                return
            job_id = jobs[-1].id

        res = requests.get('%s/jobs/%s/logs' % (api_url, job_id),
            headers={'Authorization': os.environ.get('RISEML_APIKEY')},
            auth=NoAuth(),
            stream=True)

        if res.status_code == 200:
            print("logs for job %s" % job_id)
            for buf in res.iter_content(4096):
                stdout.write(buf)
                stdout.flush()

    parser.set_defaults(run=run)


def add_kill_parser(subparsers):
    parser = subparsers.add_parser('kill', help="kill job")
    parser.add_argument('job', help="job identifier (optional)", nargs='?')
    def run(args):
        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)

        job_id = None
        if args.job:
            job_id = args.job
        else:
            repository = get_repository(get_repo_name())
            jobs = client.get_repository_jobs(repository.id)
            if not jobs:
                return
            if jobs[-1].state not in ('PENDING', 'SCHEDULED', 'TASK_RUNNING'):
                return
            job_id = jobs[-1].id

        try:
            job = client.kill_job(job_id)[0]
        except ApiException as e:
            body = json.loads(e.body)
            handle_error(body['message'], e.status)
        print("job killed (%s)" % (job.id))

    parser.set_defaults(run=run)


def add_push_parser(subparsers):
    parser = subparsers.add_parser('push', help="run new job")
    parser.add_argument('name', help="service name (optional)", nargs='?')
    parser.add_argument('--branch', help="git branch")
    parser.add_argument('--notebook', help="run notebook", action='store_true')
    parser.set_defaults(notebook=False)
    def run(args):
        if not args.name and args.notebook:
            handle_error("notebook requires name")

        branch = args.branch
        if not branch:
            proc = subprocess.Popen([resolve_path('git'), 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=get_repo_root(),
                stdout=subprocess.PIPE,
                stderr=dev_null)
            branch = proc.stdout.read().strip()

        proc = subprocess.Popen([resolve_path('git'), 'rev-parse', '--verify', branch],
            cwd=get_repo_root(),
            stdout=subprocess.PIPE,
            stderr=dev_null)
        revision = proc.stdout.read().strip()

        repo_name = get_repo_name()
        user = get_user()

        o = urlparse(git_url)
        auth_git_url = '%s://%s:%s@%s/%s.git' % (
            o.scheme, user.username, os.environ.get('RISEML_APIKEY'),
            o.netloc, repo_name)

        proc = subprocess.Popen([resolve_path('git'), 'push', auth_git_url, branch],
            cwd=get_repo_root(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)

        for buf in proc.stdout:
            stdout.write(buf)
            stdout.flush()

        res = proc.wait()
        if res != 0:
            sys.exit(res)

        res = requests.post('%s/changesets' % api_url,
            data={
                'revision': revision,
                'repository': repo_name,
                'service_name': args.name,
                'notebook': args.notebook and '1' or '0',
            },
            headers={'Authorization': os.environ.get('RISEML_APIKEY')},
            auth=NoAuth(),
            stream=True)

        if res.status_code != 200:
            handle_http_error(res)
        elif args.notebook:
            content = b''
            pattern = r'The Jupyter Notebook is running at: .+(\?token=.+)?\n'
            url = user_url % args.name
            search = True

            for buf in res.iter_content(4096):
                content += buf
                stdout.write(buf)
                stdout.flush()
                if search:
                    match = re.search(pattern, content)
                    if match:
                        token = match.group(1) or ''
                        print('notebook url: %s' % url + token)
                        webbrowser.open(url + token)
                        search = False
        else:
            for buf in res.iter_content(4096):
                stdout.write(buf)
                stdout.flush()

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
                    status = job.state
                    if job.reason:
                        status += ': ' + job.reason
                    res.append("%s (%s)" % (job.id, status))
                else:
                    if job.state in ('PENDING', 'SCHEDULED', 'TASK_RUNNING'):
                        status = job.state
                        if job.reason:
                            status += ': ' + job.reason
                        res.append("%s (%s)" % (job.id, status))
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


def main():
    parser = get_parser()
    args = parser.parse_args(sys.argv[1:])
    if args.v:
        print('RISEML_API_ENDPOINT: %s' % api_url)
        print('RISEML_SCRATCH_ENDPOINT: %s' % scratch_url)
        print('RISEML_GIT_ENDPOINT: %s' % git_url)
        print('RISEML_USER_ENDPOINT: %s' % user_url)
    if hasattr(args, 'run'):
        args.run(args)
    else:
        parser.print_usage()


if __name__ == '__main__':
    main()
