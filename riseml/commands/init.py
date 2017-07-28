from riseml.project import init_project


def add_init_parser(subparsers):
    parser = subparsers.add_parser('init', help="create config file for this directory")
    parser.add_argument('-f', '--config-file', help="config file to create", type=str, default='riseml.yml')
    parser.add_argument('-n', '--project-name', help="project name (directory name as default)", type=str)
    parser.set_defaults(run=run_init)


def run_init(args):
    init_project(args.config_file, args.project_name)