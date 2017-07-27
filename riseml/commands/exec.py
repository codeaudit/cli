import json

from ..push import push_project


def add_exec_parser(subparsers):
    parser = subparsers.add_parser('exec', help="execute single command")
    parser.add_argument('image', help="docker image to use", type=str)
    parser.add_argument('--gpus', help="number of GPUs", type=int, default=0)
    parser.add_argument('--mem', help="RAM in megabytes", type=int, default=2048)
    parser.add_argument('--cpus', help="number of CPUs", type=int, default=2)
    parser.add_argument('command', help="command with optional arguments", nargs='*')
    parser.set_defaults(run=exec_command)


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