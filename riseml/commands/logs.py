from riseml.client import DefaultApi, ApiClient

from riseml.consts import API_URL, DEFAULT_CONFIG_NAME
from riseml.project import get_project
from riseml.configs import get_project_name
from riseml.stream import stream_training_log


def add_logs_parser(subparsers):
    parser = subparsers.add_parser('logs', help="show logs")
    parser.add_argument('-f', '--config-file', help="config file to use", type=str, default=DEFAULT_CONFIG_NAME)
    parser.add_argument('experiment', help="experiment identifier (optional)", nargs='?')
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)

    if args.experiment:
        training_id, _, experiment_id = args.experiment.partition('.')
        training = client.get_training(training_id)
    else:
        project = get_project(get_project_name(args.config_file))
        trainings = client.get_repository_trainings(project.id)
        if not trainings:
            return
        training = trainings[0]
        experiment_id = None

    stream_training_log(training, experiment_id)
