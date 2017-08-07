from riseml.client import DefaultApi, ApiClient
from riseml.client.rest import ApiException

from riseml.project import get_project
from riseml.configs import get_project_name
from riseml.consts import API_URL, DEFAULT_CONFIG_NAME
from riseml.errors import handle_http_error

def add_kill_parser(subparsers):
    parser = subparsers.add_parser('kill', help="kill on-going experiment or experiment series")
    parser.add_argument('-f', '--config-file', help="config file to use", type=str, default=DEFAULT_CONFIG_NAME)
    parser.add_argument('experiments', help="experiment/series identifier (optional)", nargs='*')
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)

    trainings = args.experiments

    if not trainings:
        project = get_project(get_project_name(args.config_file))
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
            handle_http_error(e.body, e.status)