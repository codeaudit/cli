from riseml.project_template import project_init_template
from riseml.configs import create_config
from riseml.errors import handle_error

from riseml.consts import DEFAULT_CONFIG_NAME


def add_init_parser(subparsers):
    parser = subparsers.add_parser('init', help="create config file for this directory")
    parser.add_argument('-f', '--config-file', help="config file to create", type=str, default=DEFAULT_CONFIG_NAME)
    parser.add_argument('-n', '--project-name', help="project name (directory name as default)", type=str)
    parser.set_defaults(run=run_init)


def run_init(args):
    result = create_config(args.config_file, project_init_template, args.project_name)

    if not result:
        handle_error('%s already exists' % args.config_file)
    else:
        print('%s successfully created' % args.config_file)