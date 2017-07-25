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
        prefix = "{:<18}| ".format(job_name)
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
    for experiment in training.experiments:
        ids_to_name[experiment.id] = 'exp. {}'.format(experiment.number)
        for job in experiment.jobs:
            ids_to_name[job.id] = 'exp. {}: {}'.format(experiment.number, job.name)
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


def add_cluster_parser(subparsers):
    parser = subparsers.add_parser('cluster', help="show cluster info")
 
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
    parser = subparsers.add_parser('kill', help="kill on-going experiment or experiment series")
    parser.add_argument('experiments', help="experiment/series identifier (optional)", nargs='*')
    def run(args):
        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)

        trainings = args.experiments

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
                if len(training.experiments) == 1:
                    print("killed experiment {}".format(training.short_id))
                else:
                    print("killed series {}".format(training.short_id))
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
    parser = subparsers.add_parser('train', help="run new experiment or experiment series")
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

def add_status_parser(subparsers):
    parser = subparsers.add_parser('status', help="show (running) experiments")
    parser.add_argument('id', help='id of specific experiment/series for which to show status', nargs='?')
    parser.add_argument('-a', '--all', help="show all experiments", action="store_const", const=True)
    parser.add_argument('-l', '--long', help="expand series", action="store_const", const=True)

    def run(args):
        def full_id(training, experiment=None, job=None):
            if len(training.experiments) > 1 and experiment:
                return '{}.{}'.format(training.short_id, experiment.number)
            else:
                return training.short_id
        
        def params(experiment):
            return ', '.join(['{}={}'.format(p, v) for p, v in json.loads(experiment.params).items()])
        
        def show_experiment(training, experiment):
            print("ID: {}".format(full_id(training, experiment)))
            print("Type: Experiment")
            print("State: {}".format(experiment.state))
            print("Image: {}".format(training.image))
            print("Framework: {}".format(training.framework))
            print("Framework Config:")
            for attribute, value in training.framework_details.to_dict().iteritems():
                if value is not None:
                    print("   {}: {}".format(attribute, value))
            print("Run Commands:")
            print(''.join(["  {}".format(command) for command in training.run_commands]))
            print("Max Parallel Experiments: {}".format(training.max_parallel_experiments))
            print("Params: {}\n".format(params(experiment)))

            header = ['JOB', 'STATE', 'STARTED', 'FINISHED', 'GPU', 'CPU', 'MEM']
            widths = [9, 13, 13, 13, 6, 6, 6]
            print(util.format_header(header, widths=widths))
            for job in experiment.jobs:
                values = [job.name, job.state, util.get_since_str(job.started_at),
                          util.get_since_str(job.finished_at)] + ['N/A'] * 3
                print(util.format_line(values, widths=widths))
        
        def print_experiments(training, with_project=True, with_type=True, with_params=True, indent=True, widths=None):
            for i, experiment in enumerate(training.experiments):
                indent_str = (u'├╴' if i < len(training.experiments) - 1 else u'╰╴') if indent else ''
                values = [indent_str + full_id(training, experiment)]
                if with_project:
                    values += [training.changeset.repository.name]
                values += [experiment.state, util.get_since_str(experiment.created_at)]
                if with_type:
                    values += [indent_str + 'Experiment']
                if with_params:
                    values += [params(experiment)]
                print(util.format_line(values, widths=widths))
        
        def show_experiment_group(training):
            print("ID: {}".format(full_id(training)))
            print("Type: Series")
            print("State: {}".format(training.state))
            print("Project: {}\n".format(training.changeset.repository.name))

            header = ['ID', 'STATE', 'AGE', 'PARAMS']
            widths = (6, 9, 13, 14)
            print(util.format_header(header, widths=widths))
            print_experiments(training, with_project=False, with_type=False, indent=False, widths=widths)

        def show_trainings(trainings, all=False, collapsed=True):
            header = ['ID', 'PROJECT', 'STATE', 'AGE', 'TYPE']
            if collapsed:
                widths = (6, 14, 9, 13, 15)
            else:
                header += ['PARAMS']
                widths = (8, 14, 9, 13, 15, 14)
            print(util.format_header(header, widths=widths))

            for training in trainings:
                if not all and training.state in ['FINISHED', 'KILLED', 'FAILED']:
                    continue
                values = [training.short_id, training.changeset.repository.name,
                        training.state, util.get_since_str(training.created_at),
                        'Experiment' if len(training.experiments) == 1 else 'Series']
                if not collapsed:
                    values += ['']
                print(util.format_line(values, widths=widths))
                if not collapsed and len(training.experiments) > 1:
                    print_experiments(training, widths=widths)
        
        api_client = ApiClient(host=api_url)
        client = DefaultApi(api_client)
        
        if args.id:
            ids = args.id.split('.')
            training = client.get_training(ids[0])
            if len(training.experiments) == 1:
                show_experiment(training, training.experiments[0])
            elif len(ids) > 1:
                experiment = next((exp for exp in training.experiments if str(exp.number) == ids[1]), None)
                if experiment:
                    show_experiment(training, experiment)
                else:
                    handle_error('Experiment not found')
            else:
                show_experiment_group(training)
        else:
            show_trainings(client.get_trainings(), all=args.all, collapsed=not args.long)

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
