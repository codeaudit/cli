import json

from riseml.client import DefaultApi, ApiClient

from riseml.configs import load_config
from riseml.user import get_user
from riseml.project import push_project
from riseml.consts import DEFAULT_CONFIG_NAME
from riseml.stream import stream_experiment_log
from riseml.util import call_api


def add_train_parser(subparsers):
    parser = subparsers.add_parser('train', help="run new experiment or experiment series")
    parser.add_argument('-f', '--config-file', help="config file to use", type=str, default=DEFAULT_CONFIG_NAME)
    parser.add_argument('-l', '--logs', help="stream logs", action='store_true')
    parser.set_defaults(run=run_train)


def run_train(args):
    config = load_config(args.config_file)
    project_name = config.project

    user = get_user()
    revision = push_project(user, project_name, args.config_file)
    api_client = ApiClient()
    client = DefaultApi(api_client)

    experiment = call_api(lambda: client.create_experiment(
        project_name, revision,
        kind='train', config=json.dumps(config.train.as_dict())
    ))
   
    if args.logs:
        stream_experiment_log(experiment)
    else:
        print('Started experiment %s. To obtain logs, type `riseml logs %s`.' % (experiment.short_id, experiment.short_id))
