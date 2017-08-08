import json

from riseml.configs import load_config, get_project_name
from riseml.user import get_user
from riseml.project import push_project
from riseml.jobs import run_job
from riseml.errors import handle_error
from riseml.consts import DEFAULT_CONFIG_NAME


def add_deploy_parser(subparsers):
    parser = subparsers.add_parser('deploy', help="run new deploy job")
    parser.add_argument('-f', '--config-file', help="config file to use", type=str, default=DEFAULT_CONFIG_NAME)
    parser.set_defaults(run=run_section)


def run_section(args):
    config = load_config(args.config_file)
    project_name = config.project

    try:
        deploy_config = config.deploy
    except AttributeError:
        handle_error('no `deploy` section in {}'.format(args.config_file))

    user = get_user()
    revision = push_project(user, project_name, args.config_file)

    run_job(project_name, revision, args.config_section, json.dumps(dict(deploy_config)))