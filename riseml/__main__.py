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


def create_project():
    cwd = os.getcwd()
    if not os.path.exists(os.path.join(cwd, 'riseml.yml')):
        project_name = os.path.basename(cwd)
        with open('riseml.yml', 'a') as f:
            f.write("project: %s\n" % project_name)
    name = get_project_name()
    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)
    project = client.create_repository(name)[0]
    print("project created: %s (%s)" % (project.name, project.id))


def handle_error(message, status_code=None):
    if status_code:
        print('ERROR: %s (%d)' % (message, status_code))
    else:
        print('ERROR: %s' % message)
    sys.exit(1)


def handle_http_error(res):
    handle_error(res.json()['message'], res.status_code)

def stream_log(url, ids_to_name):

    def print_log_message(msg):
        for line in msg['log_lines']:
            last_color = job_ids_last_color_used.get(msg['job_id'], '')
            output = "%s%s%s%s" % (message_prefix(msg), last_color, line, util.ansi_sequence(0))
            used_colors = ANSI_ESCAPE_REGEX.findall(line)
            if used_colors:
                job_ids_last_color_used[msg['job_id']] = used_colors[-1]
            print output

    def print_state_message(msg):
        state = "--> %s" % msg['new_state']
        output = "%s%s" % (message_prefix(msg),
                           util.color_string("bold_white", state))
        print(output)

    def message_prefix(msg):
        job_name = ids_to_name[msg['job_id']]
        color = job_ids_color[msg['job_id']]
        prefix = "{:<17}| ".format(job_name)
        return util.color_string(color, prefix)

    job_ids_color = {id: util.COLOR_CODES.keys()[(i + 1) % len(util.COLOR_CODES)] 
                     for i, id in enumerate(ids_to_name.keys())}
    job_ids_last_color_used = {}
    
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

def stream_job_log(job):
    def flatten_jobs(job):
        for c in job.children:
            for j in flatten_jobs(c):
                yield j
        yield job

    jobs = list(flatten_jobs(job))
    ids_to_name = { job.id: util.get_job_name(job) for job in jobs }
    url = '%s/ws/jobs/%s/stream' % (stream_url, job.id)
    stream_log(url, ids_to_name)

def stream_training_log(training):
    url = '%s/ws/trainings/%s/stream' % (stream_url, training.id)
    ids_to_name = {}
    ids_to_name[training.id] = 'training'
    for run in training.runs:
        ids_to_name[run.id] = 'run {}'.format(run.number)
        for job in run.jobs:
            ids_to_name[job.id] = 'run {}: {}'.format(run.number, job.name)
    for job in training.jobs:
        if job.id not in ids_to_name:
            ids_to_name[job.id] = job.name
    stream_log(url, ids_to_name)

def load_config(config_file, config_section):
    if not os.path.exists(config_file):
        handle_error("%s does not exist" % config_file)
    with open(config_file, 'r') as f:
        config = yaml.load(f.read())
        if config_section not in config:
            handle_error("config doesn't contain section for %s" % config_section)
        return config[config_section]


def run_job(project_name, revision, kind, config):
    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)
    try:
        jobs = client.create_job(project_name, revision, kind=kind, 
                                 config=config)
    except ApiException as e:
        body = json.loads(e.body)
        handle_error(body['message'], e.status)        
    stream_job_log(jobs[0])


def run_section(args):
    project_name = get_project_name()
    # TODO: validate config here already
    config_section = load_config(args.config_file, args.config_section)
    user = get_user()
    revision = push_project(user, project_name)
    run_job(project_name, revision, args.config_section, 
            json.dumps(config_section))


def exec_command(args):
    project_name = get_project_name()
    config = {
        'image': {
            'name': args.image
        },
        'resources': {
            'cpus': args.cpus,
            'mem': args.mem,
            'gpus': args.gpus
        },
        'run': [' '.join(args.command)]
    }
    # TODO: validate config here already
    user = get_user()
    revision = push_project(user, project_name)
    run_job(project_name, revision, 'train', json.dumps(config))


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


def add_whoami_parser(subparsers):
    parser = subparsers.add_parser('whoami', help="show currently logged in user")
    def run(args):
        user = get_user()
        print("%s (%s)" % (user.username, user.id))

    parser.set_defaults(run=run)


def add_clusterinfo_parser(subparsers):
    parser = subparsers.add_parser('clusterinfo', help="show cluster info")
 
    def run(args):
        api_client = ApiClient(host=api_url)
        client = AdminApi(api_client)        
        nodes = client.get_nodes()
        print("RiseML cluster nodes:\n")
        print("{:<18}  {:>6} {:>9} {:>4}".format('Hostname', 'CPUs', 'MEM(GiB)', 'GPUs'))
        width = 18 + 6 + 9 + 2 + 6
        total_cpus = 0
        total_mem = 0
        total_gpus = 0
        print('-' * width)       
        for n in nodes:
            print("{:<18}  {:>6} {:>9} {:>4}".format(n.hostname, n.cpus, "%.1f" % (float(n.mem) * (10 ** 6) / (1024 ** 3)), n.gpus))
            total_cpus += n.cpus
            total_mem += n.mem
            total_gpus += n.gpus
        print('-' * width)
        print("{:<18}  {:>6} {:>9} {:>4}".format('Total', total_cpus, "%.1f" % (float(total_mem) * (10 ** 6) / (1024 ** 3)), total_gpus))
    parser.set_defaults(run=run)

def add_logs_parser(subparsers):
    parser = subparsers.add_parser('logs', help="show logs")
    parser.add_argument('training', help="job identifier (optional)", nargs='?')
    def run(args):
        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)
        if args.training:
            training = client.get_training(args.training)
        else:
            project = get_project(get_project_name())
            trainings = client.get_repository_trainings(project.id)
            if not trainings:
                return
            training = trainings[0]

        stream_training_log(training)
    parser.set_defaults(run=run)


def add_kill_parser(subparsers):
    parser = subparsers.add_parser('kill', help="kill training")
    parser.add_argument('trainings', help="training identifier (optional)", nargs='*')
    def run(args):
        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)

        trainings = args.trainings

        if not trainings:
            project = get_project(get_project_name())
            trainings = client.get_repository_trainings(project.id)
            if not trainings:
                return
            if trainings[0].state in ('FINISHED', 'FAILED', 'KILLED'):
                return
            trainings = [trainings[0].id]
        for training_id in trainings:
            try:
                training = client.kill_training(training_id)
                print("killed training %s (%s)" % (training.short_id, training.id))
            except ApiException as e:
                body = json.loads(e.body)
                print('ERROR: %s (%s)' % (body['message'], e.status))
            
    parser.set_defaults(run=run)


def push_project(user, project_name):
    o = urlparse(git_url)
    prepare_url = '%s://%s/%s/users/%s/repositories/%s/sync/prepare' % (
        o.scheme, o.netloc, o.path, user.id, project_name)
    done_url = '%s://%s/%s/users/%s/repositories/%s/sync/done' % (
        o.scheme, o.netloc, o.path, user.id, project_name)
    res = requests.post(prepare_url)
    if res.status_code == 412 and 'Repository does not exist' in res.json()['message']:
        create_project()
        res = requests.post(prepare_url)
    if res.status_code != 200:
        handle_http_error(res)
    sync_path = res.json()['path']
    o = urlparse(sync_url)
    rsync_url = '%s://%s%s/%s' % (
        o.scheme, o.netloc, o.path, sync_path)
    project_root = os.path.join(get_project_root(), '')
    exclude_file = os.path.join(project_root, '.risemlignore')
    sys.stderr.write("Pushing code...")
    sync_cmd = [resolve_path('rsync'),
                '-rlpt',
                '--exclude=.git',
                '--delete-during',
                project_root,
                rsync_url]
    if os.path.exists(exclude_file):
        sync_cmd.insert(2, '--exclude-from=%s' % exclude_file)
    proc = subprocess.Popen(sync_cmd,
                            cwd=project_root,
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


def add_exec_parser(subparsers):
    parser = subparsers.add_parser('exec', help="execute single command")
    parser.add_argument('image', help="docker image to use", type=str)
    parser.add_argument('--gpus', help="number of GPUs", type=int, default=0)
    parser.add_argument('--mem', help="RAM in megabytes", type=int, default=2048)
    parser.add_argument('--cpus', help="number of CPUs", type=int, default=2)
    parser.add_argument('command', help="command with optional arguments", nargs='*')
    parser.set_defaults(run=exec_command)


def add_train_parser(subparsers):
    parser = subparsers.add_parser('train', help="run new training job")
    parser.add_argument('-f', '--config-file', help="config file to use", type=str, default='riseml.yml')

    def run(args):
        project_name = get_project_name()
        # TODO: validate config here already
        config_section = load_config(args.config_file, 'train')
        user = get_user()
        revision = push_project(user, project_name)
        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)
        try:
            training = client.create_training(project_name, revision, kind='train', config=json.dumps(config_section))
        except ApiException as e:
            body = json.loads(e.body)
            handle_error(body['message'], e.status)
        stream_training_log(training)
    
    parser.set_defaults(run=run)


def add_deploy_parser(subparsers):
    parser = subparsers.add_parser('deploy', help="run new deploy job")
    parser.add_argument('-f', '--config-file', help="config file to use", type=str, default='riseml.yml')     
    parser.set_defaults(config_section='deploy')
    parser.set_defaults(run=run_section)

def add_ps_parser(subparsers):
    parser = subparsers.add_parser('ps', help="show trainings")
    parser.add_argument('-a', help = "show all trainings", action="store_const", const=True)
    parser.add_argument('-l', help = "show more info", action="store_const", const=True)

    def run(args):
        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)
        trainings = client.get_trainings()

        header = ['ID', 'PROJECT', 'STATE', 'AGE', 'FINISHED RUNS', 'ACTIVE JOBS']
        widths = (4, 14, 9, 13, 14, 10)
        print(util.format_header(header, widths=widths))

        for training in trainings:
            if not args.a and training.state in ['FINISHED', 'KILLED', 'FAILED']:
                continue
            values = [training.short_id, training.changeset.repository.name,
                      training.state, util.get_since_str(training.created_at),
                      # Finished runs
                      '{}/{}'.format(len([run for run in training.runs if run.state == 'FINISHED']),
                                     len(training.runs)),
                      # Active jobs
                      '{}'.format(training.active_job_count)]
            print(util.format_line(values, widths=widths))
    
    parser.set_defaults(run=run)

def add_info_parser(subparsers):
    parser = subparsers.add_parser('info', help="show training details")
    parser.add_argument('training_id', help="id of trainining")

    def format_job(job):
        return "{} ({} since {})".format(job.name, job.state, util.get_since_str(job.state_changed_at))

    def run(args):
        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)
        training = client.get_training(args.training_id)
        print("ID: {}".format(training.short_id))
        print("UUID: {}".format(training.id))
        print("State: {}".format(training.state))
        print("Image: {}".format(training.image))
        print("Framework: {}".format(training.framework))
        print("Framework Config:")
        for attribute, value in training.framework_details.to_dict().iteritems():
            if value is not None:
                print("   {}: {}".format(attribute, value))
        print("Run Commands:")
        print(''.join(["  {}".format(command) for command in training.run_commands]))
        print("Max Parallel Runs: {}\n".format(training.max_parallel_runs))

        header = ['RUN', 'STATE', 'STARTED', 'FINISHED', 'JOBS', 'PARAMS']
        widths = [4, 9, 13, 13, 40, 20]
        print(util.format_header(header, widths=widths))
        for run in training.runs:
            values = [run.number, run.state, util.get_since_str(run.started_at),
                      util.get_since_str(run.finished_at),
                      format_job(run.jobs[0]),
                      ', '.join(['{} = {}'.format(p, v) for p, v in json.loads(run.params).items()])]
            print(util.format_line(values, widths=widths))
            for job in run.jobs[1:]:
                print(util.format_line([''] * 4 + [format_job(job)] + [''], widths=widths))
    
    parser.set_defaults(run=run)

def add_ps_old_parser(subparsers):
    parser = subparsers.add_parser('ps-old', help="show jobs")
    parser.add_argument('-a', help="show all jobs",
        action='store_const', const=True)
    parser.add_argument('-l', help="show more info",
        action='store_const', const=True)

    def run(args):

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

        def get_column_values(job, project, name, cols):
            vals = []
            for c in cols:
                if c == 'project':
                    vals.append(project)
                elif c == 'name':
                    vals.append(name)
                elif c == 'since':
                    vals.append(util.get_since_str(job.state_changed_at))
                else:
                    v = getattr(job, c)
                    vals.append(v or '-')
            return vals

        def print_job(j, project, cols, depth=0, siblings_at=[],
                      format_line=util.format_line):
            index = index = getattr(j, 'index', None)
            name = get_indent(depth, siblings_at, index=index) + util.get_job_name(j)
            values = get_column_values(j, project, name, cols)
            print(format_line(values))
            if j.name == 'sequence':
                j.children = order_children(j.children)
            if j.children:
                siblings_at.append(depth)
                depth += 1
                for i, c in enumerate(j.children):
                    if i == len(j.children) - 1:
                        siblings_at.pop()
                    print_job(c, project, cols, depth, siblings_at,
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

        header = ['ID', 'PROJECT', 'STATE', 'SINCE', 'NAME']
        widths = (4, 10, 9, 13, 8)
        columns = ['short_id', 'project', 'state', 'since', 'name']

        if args.l:
            header = ['ID', 'UUID', 'PROJECT', 'CPUS', 'GPUS', 'MEM', 'STATE', 'SINCE', 'NAME']
            widths = (4, 36, 10, 4, 4, 4, 9, 12, 8)
            columns = ['short_id', 'id', 'project', 'cpus', 'gpus', 'mem', 'state', 'since', 'name']

        if all_jobs:
            print(util.format_header(header, widths=widths))
        for j in all_jobs:
            print_job(j, j.changeset.repository.name, columns,
                      format_line=lambda x: util.format_line(x, widths=widths))


    parser.set_defaults(run=run)


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', help="show endpoints",
        action='store_const', const=True)

    subparsers = parser.add_subparsers()

    # user ops
    add_register_parser(subparsers)
    add_whoami_parser(subparsers)

    # clusterinfo ops
    add_clusterinfo_parser(subparsers)

    # worklow ops
    add_train_parser(subparsers)
    add_exec_parser(subparsers)
    add_deploy_parser(subparsers)
    add_logs_parser(subparsers)
    add_kill_parser(subparsers)
    add_ps_old_parser(subparsers)
    add_ps_parser(subparsers)
    add_info_parser(subparsers)

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
