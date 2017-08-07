import json

from riseml.configs import load_config
from riseml.user import get_user
from riseml.project import push_project, get_project_name
from riseml.jobs import run_job
from riseml.consts import DEFAULT_CONFIG_NAME


def add_deploy_parser(subparsers):
    parser = subparsers.add_parser('deploy', help="run new deploy job")
    parser.add_argument('-f', '--config-file', help="config file to use", type=str, default=DEFAULT_CONFIG_NAME)
    parser.set_defaults(config_section='deploy')
    parser.set_defaults(run=run_section)


def run_section(args):
    project_name = get_project_name(args.config_file)

    config_section = load_config(args.config_file, args.config_section)
    user = get_user()
    revision = push_project(user, project_name, args.config_file)

    run_job(project_name, revision, args.config_section, json.dumps(dict(config_section)))