import json

from riseml.client import DefaultApi, ApiClient
from riseml.client.rest import ApiException

from ..push import push_project

def add_deploy_parser(subparsers):
    parser = subparsers.add_parser('deploy', help="run new deploy job")
    parser.add_argument('-f', '--config-file', help="config file to use", type=str, default='riseml.yml')
    parser.set_defaults(config_section='deploy')
    parser.set_defaults(run=run_section)

def run_section(args):
    project_name = get_project_name()
    # TODO: validate config here already
    config_section = load_config(args.config_file, args.config_section)
    user = get_user()
    revision = push_project(user, project_name)
    run_job(project_name, revision, args.config_section,
            json.dumps(config_section))

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