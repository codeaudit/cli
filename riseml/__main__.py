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

from threading import Thread

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from . import util


from riseml.client import DefaultApi, AdminApi, ScratchEntry, ApiClient
from riseml.client.rest import ApiException
from riseml.config_parser import parse_file

try:
    stdout = sys.stdout.buffer
except AttributeError:
    stdout = sys.stdout


try:
    from subprocess import dev_null  # py3
except ImportError:
    import os
    dev_null = open(os.devnull, 'wb')


endpoint_url = os.environ.get('RISEML_ENDPOINT', 'http://127.0.0.1:8080')
sync_url = os.environ.get('RISEML_SYNC_ENDPOINT', 'rsync://192.168.99.100:31876/sync')
user_url = os.environ.get('RISEML_USER_ENDPOINT', 'https://%s.riseml.io')
api_url = endpoint_url + '/api'
git_url = endpoint_url + '/git'
o = urlparse(endpoint_url)
stream_url = "ws://%s/stream" % o.netloc

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
    if os.path.exists(os.path.join(cwd, 'riseml.yml')):
        return cwd
    elif cwd != '/':
        return get_repo_root(os.path.dirname(cwd))


def get_repo_name():
    repo_root = get_repo_root()
    if not repo_root:
        handle_error("no riseml repository found")
    config = parse_file(os.path.join(repo_root, 'riseml.yml'))
    return config.repository


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


def stream_log(job):

    def print_log_message(msg):
        for line in msg['log_lines']:
            output = "%s%s" % (message_prefix(msg), line)
            print(output)

    def print_state_message(msg):
        state = "--> %s" % msg['new_state']
        output = "%s%s" % (message_prefix(msg),
                           util.color_string("bold_white", state))
        print(output)

    def message_prefix(msg):
        job_name = util.get_job_name(job_ids[msg['job_id']])
        color = job_ids_color[msg['job_id']]
        prefix = "{:<12}| ".format(job_name)
        return util.color_string(color, prefix)

    def flatten_jobs(job):
        for c in job.children:
            for j in flatten_jobs(c):
                yield j
        yield job

    jobs = list(flatten_jobs(job))
    job_ids = {j.id: j for j in jobs}
    job_ids_color = {j.id: util.COLOR_NAMES[(i + 2) % len(util.COLOR_NAMES)] 
                     for i, j in enumerate(jobs)}
    job_ids_color[job.id] = 'white'
    url = '%s/ws/jobs/%s/stream' % (stream_url, job.id)

    def on_message(ws, message):
        msg = json.loads(message)

        msg_type = msg['type']
        if msg_type == 'log':
            print_log_message(msg)
        elif msg_type == 'state':
            print_state_message(msg)

    def on_error(ws, error):
        handle_error(error)

    def on_close(ws):
        # print("Stream closed")
        sys.exit(0)

    ws = websocket.WebSocketApp(
        url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # FIXME: {'Authorization': os.environ.get('RISEML_APIKEY')}
    ws.run_forever()


def run_command(args):
    repo_name = get_repo_name()
    user = get_user()
    revision = push_repo(user, repo_name)
    if not args.section and not args.kind:
        args.kind = 'train'

    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)

    arg_list = [
        ('notebook', args.notebook and '1' or '0'),
        ('gpus', args.gpus),
        ('cpus', args.cpus),
        ('mem', args.mem),
        ('command', ' '.join(args.command)),
        ('image', args.image),
        ('kind', args.kind),
    ]
    kwargs = {k: v for k, v in arg_list if v not in (None, [], '')}

    jobs = client.create_job(repo_name, revision, args.section or 'adhoc',
                             **kwargs)

    if args.notebook:
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
        stream_log(jobs[0])


def add_create_parser(subparsers):
    parser = subparsers.add_parser('create', help="create repository")
    def run(args):
        cwd = os.getcwd()
        if not os.path.exists(os.path.join(cwd, 'riseml.yml')):
            repo_name = os.path.basename(cwd)
            with open('riseml.yml', 'a') as f:
                f.write("repository: %s\n" % repo_name)
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
        job = None
        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)
        if args.job:
            jobs = client.get_job(args.job)
            job = jobs[0]
        else:
            repository = get_repository(get_repo_name())
            jobs = client.get_repository_jobs(repository.id)
            if not jobs:
                return
            job = jobs[0]

        stream_log(job)
    parser.set_defaults(run=run)


def add_kill_parser(subparsers):
    parser = subparsers.add_parser('kill', help="kill job")
    parser.add_argument('jobs', help="job identifier (optional)", nargs='*')
    def run(args):
        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)

        jobs = args.jobs

        if not jobs:
            repository = get_repository(get_repo_name())
            jobs = client.get_repository_jobs(repository.id)
            if not jobs:
                return
            if jobs[0].state in ('FINISHED', 'FAILED', 'KILLED'):
                return
            jobs = [jobs[0].id]
        for job_id in jobs:
            try:
                job = client.kill_job(job_id)[0]
                print("killed %s job %s (%s)" % (job.name, job.short_id, job.id))
            except ApiException as e:
                body = json.loads(e.body)
                print('ERROR: %s (%s)' % (body['message'], e.status))
            
    parser.set_defaults(run=run)


def add_push_parser(subparsers):
    parser = subparsers.add_parser('push', help="push current code")
    parser.set_defaults(notebook=False)
    def run(args):
        repo_name = get_repo_name()
        user = get_user()
        revision = push_repo(user, repo_name)
        print("new revision: %s" % revision)
    parser.set_defaults(run=run)


def push_repo(user, repo_name):
    o = urlparse(git_url)
    prepare_url = '%s://%s/%s/users/%s/repositories/%s/sync/prepare' % (
        o.scheme, o.netloc, o.path, user.id, repo_name)
    done_url = '%s://%s/%s/users/%s/repositories/%s/sync/done' % (
        o.scheme, o.netloc, o.path, user.id, repo_name)
    res = requests.post(prepare_url)
    if res.status_code != 200:
        handle_http_error(res)
    sync_path = res.json()['path']
    o = urlparse(sync_url)
    rsync_url = '%s://%s%s/%s' % (
        o.scheme, o.netloc, o.path, sync_path)
    repo_root = os.path.join(get_repo_root(), '')
    exclude_file = os.path.join(repo_root, '.risemlignore')
    sys.stderr.write("Pushing code...")
    sync_cmd = [resolve_path('rsync'),
                '-rlpt',
                '--exclude=.git',
                '--delete-during',
                repo_root,
                rsync_url]
    if os.path.exists(exclude_file):
        sync_cmd.insert(2, '--exclude-from=%s' % exclude_file)
    proc = subprocess.Popen(sync_cmd,
                            cwd=repo_root,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    for buf in proc.stdout:
        stdout.write(buf)
        stdout.flush()

    res = proc.wait()
    if res != 0:
        sys.exit(res)
    res = requests.post(done_url, params={'path': sync_path})
    if res.status_code != 200:
        handle_http_error(res)
    revision = res.json()['sha']
    print("done")
    return revision


def add_run_parser(subparsers):
    parser = subparsers.add_parser('run', help="run new job")
    parser.add_argument('--notebook', help="run notebook", action='store_true')
    parser.add_argument('--image', help="docker image to use", type=str)
    parser.add_argument('--gpus', help="number of GPUs", type=int)
    parser.add_argument('--mem', help="RAM in megabytes", type=int)
    parser.add_argument('--cpus', help="number of CPUs", type=int)
    parser.add_argument('--section', '-s', help="riseml.yml config section")
    parser.add_argument('--kind', '-k', choices=['train', 'deploy'], help="riseml.yml config section")
    parser.add_argument('command', help="command with optional arguments", nargs='*')
    parser.set_defaults(notebook=False)
    parser.set_defaults(run=run_command)


def add_train_parser(subparsers):
    parser = subparsers.add_parser('train', help="run new training job")
    parser.add_argument('--notebook', help="run notebook", action='store_true', default=False)
    parser.add_argument('--image', help="docker image to use", type=str)
    parser.add_argument('--gpus', help="number of GPUs", type=int)
    parser.add_argument('--mem', help="RAM in megabytes", type=int)
    parser.add_argument('--cpus', help="number of CPUs", type=int)
    parser.add_argument('command', help="command with optional arguments", nargs='*')
    parser.set_defaults(section='train')
    parser.set_defaults(kind='train')
    parser.set_defaults(run=run_command)


def add_deploy_parser(subparsers):
    parser = subparsers.add_parser('deploy', help="run new deploy job")
    parser.add_argument('--notebook', help="run notebook", action='store_true', default=False)
    parser.add_argument('--image', help="docker image to use", type=str)
    parser.add_argument('--gpus', help="number of GPUs", type=int)
    parser.add_argument('--mem', help="RAM in megabytes", type=int)
    parser.add_argument('--cpus', help="number of CPUs", type=int)
    parser.add_argument('command', help="command with optional arguments", nargs='*')
    parser.set_defaults(section='deploy')
    parser.set_defaults(kind='deploy')
    parser.set_defaults(run=run_command)


def add_ps_parser(subparsers):
    parser = subparsers.add_parser('ps', help="show jobs")
    parser.add_argument('-a', help="show all jobs",
        action='store_const', const=True)
    parser.add_argument('-l', help="show more info",
        action='store_const', const=True)

    def run(args):

        def format_header(columns,  widths=(4, 10, 9, 8)):
            def bold(s):
                return '\033[1m{}\033[0m'.format(s)
            header = ''
            for i, w in enumerate(widths):
                header += '{:%s{widths[%s]}} ' % ('<', i)
            return bold(header.format(*columns,
                                      widths=widths))

        def format_line(columns, widths=(4, 10, 9, 8)):
            line = '{:>{widths[0]}} {:<{widths[1]}} {:>{widths[2]}} {:<{widths[3]}}'
            line = ''
            for i, w in enumerate(widths):
                line += '{:%s{widths[%s]}} ' % ('<', i)
            return line.format(*columns,
                               widths=widths)

        def order_children(children):
            next_c = {}
            first_c = None
            for c in children:
                if c.previous_job:
                    next_c[c.previous_job] = c
                else:
                    first_c = c
            seq = [first_c]
            first_c.index = 1
            index = 2
            while first_c.id in next_c:
                first_c = next_c[first_c.id]
                first_c.index = index
                index += 1
                seq.append(first_c)
            return seq

        def get_since_str(timestamp):
            if not timestamp:
                return '-'
            now = int(time.time() * 1000)
            since_ms = now - timestamp
            days, since_ms = divmod(since_ms, 24 * 60 * 60 * 1000)
            hours, since_ms = divmod(since_ms, 60 * 60 * 1000)
            minutes, since_ms = divmod(since_ms, 60 * 1000)
            seconds, since_ms = divmod(since_ms, 1000)
            if days > 0:
                return "%s day(s)" % days
            elif hours > 0:
                return "%s hour(s)" % hours
            elif minutes > 0:
                return "%s minute(s)" % minutes
            elif seconds > 0:
                return "%s second(s)" % seconds
            else:
                return "just now"

        def get_column_values(job, repo, name, cols):
            vals = []
            for c in cols:
                if c == 'repo':
                    vals.append(repo)
                elif c == 'name':
                    vals.append(name)
                elif c == 'since':
                    vals.append(get_since_str(job.state_changed_at))
                else:
                    v = getattr(job, c)
                    vals.append(v or '-')
            return vals

        def print_job(j, repo, cols, depth=0, siblings_at=[],
                      format_line=format_line):
            index = index = getattr(j, 'index', None)
            name = get_indent(depth, siblings_at, index=index) + util.get_job_name(j)
            values = get_column_values(j, repo, name, cols)
            print(format_line(values))
            if j.name == 'sequence':
                j.children = order_children(j.children)
            if j.children:
                siblings_at.append(depth)
                depth += 1
                for i, c in enumerate(j.children):
                    if i == len(j.children) - 1:
                        siblings_at.pop()
                    print_job(c, repo, cols, depth, siblings_at,
                              format_line=format_line)

        def get_indent(depth, siblings_at, index=None):
            indent = ""
            for i in range(0, depth):
                if i == depth - 1:
                    indent += ' {:<3}'.format('\_%s ' % ('' if index is None else index))
                elif i in siblings_at:
                    indent += ' {:<3}'.format('|')
                else:
                    indent += ' {:<3}'.format(' ')
            return indent

        #def print_test(t, depth=0, siblings_at=[]):
        #    name = get_indent(depth, siblings_at) + t['name']
        #    print(format_line([t['name'], t['name'], t['name'], name], widths=(10, 10, 12, 10)))
        #    if 'children' in t:
        #        siblings_at.append(depth)
        #        depth += 1
        #        for i, c in enumerate(t['children']):
        #            if i == len(t['children']) - 1:
        #                siblings_at.pop()
        #            print_test(c, depth, siblings_at)
        #t = {
        #    'name': 'p1',
        #    'children': [
        #        {'name': 'p1c1'},
        #        {'name': 'p1c2'},
        #        {'name': 'p1c3', 'children': [
        #            {'name': 'p1c3c1'},
        #            {'name': 'p1c3c2', 'children': [
        #                {'name': 'p1c3c2c1'},
        #                {'name': 'p1c3c2c2'},
        #            ]},
        #            {'name': 'p1c3c3'},
        #        ]},
        #        {'name': 'p1c4'},
        #        {'name': 'p1c5', 'children': [
        #            {'name': 'p1c5c1'},
        #            {'name': 'p1c5c2', 'children': [
        #                {'name': 'p1c5c2c1'},
        #                {'name': 'p1c5c2c2'},
        #            ]},
        #            {'name': 'p1c5c3'},
        #        ]},
        #    ]
        #}
        #print_test(t)

        def filter_jobs(jobs):
            res = []
            for job in jobs:
                if args.a:
                    res.append(job)
                else:
                    if job.state in ('PENDING', 'STARTING', 'RUNNING',
                                     'BUILDING', 'SERVING'):
                        res.append(job)
            return res

        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)
        all_jobs = filter_jobs(client.get_jobs(only_root=True))

        header = ['ID', 'REPO', 'STATE', 'SINCE', 'NAME']
        widths = (4, 10, 9, 13, 8)
        columns = ['short_id', 'repo', 'state', 'since', 'name']

        if args.l:
            header = ['ID', 'UUID', 'REPO', 'CPUS', 'GPUS', 'MEM', 'STATE', 'SINCE', 'NAME']
            widths = (4, 36, 10, 4, 4, 4, 9, 12, 8)
            columns = ['short_id', 'id', 'repo', 'cpus', 'gpus', 'mem', 'state', 'since', 'name']

        if all_jobs:
            print(format_header(header, widths=widths))
        for j in all_jobs:
            print_job(j, j.changeset.repository.name, columns,
                      format_line=lambda x: format_line(x, widths=widths))


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
    add_train_parser(subparsers)
    add_run_parser(subparsers)
    add_deploy_parser(subparsers)
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
