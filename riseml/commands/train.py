import json

from riseml.client import DefaultApi, ApiClient
from riseml.client.rest import ApiException

from riseml.configs import load_config
from riseml.user import get_user
from riseml.errors import handle_error
from riseml.project import push_project, get_project_name
from riseml.consts import API_URL
from riseml.stream import stream_training_log


def add_train_parser(subparsers):
    parser = subparsers.add_parser('train', help="run new experiment or experiment series")
    parser.add_argument('-f', '--config-file', help="config file to use", type=str, default='riseml.yml')
    parser.set_defaults(run=run_train)


def run_train(args):
    project_name = get_project_name()

    # TODO: validate config here already
    config_section = load_config(args.config_file, 'train')
    user = get_user()
    revision = push_project(user, project_name)
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)

    try:
        training = client.create_training(project_name, revision, kind='train', config=json.dumps(config_section))
    except ApiException as e:
        body = json.loads(e.body)
        handle_error(body['message'], e.status)

    stream_training_log(training, None)
