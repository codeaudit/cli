from riseml.client import DefaultApi, ApiClient
from riseml.client.rest import ApiException

from riseml.consts import API_URL, DEFAULT_CONFIG_NAME
from riseml.errors import handle_http_error, handle_error

def add_kill_parser(subparsers):
    parser = subparsers.add_parser('kill', help="kill on-going experiment or experiment series")
    parser.add_argument('experiments', help="experiment/series identifier (optional)", nargs='*')
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)

    trainings = args.experiments

    if not trainings:
        try:
            trainings = client.get_trainings()
        except ApiException as e:
            handle_http_error(e.body, e.status)

        if not trainings:
            handle_error('No trainings to kill')

        if trainings[0].state in ('FINISHED', 'FAILED', 'KILLED'):
            handle_error('No trainings to kill')

        trainings = [trainings[0].id]

    for training_id in trainings:
        try:
            training = client.kill_training(training_id)
        except ApiException as e:
            handle_http_error(e.body, e.status)

        if len(training.experiments) == 1:
            print("killed experiment {}".format(training.short_id))
        else:
            print("killed series {}".format(training.short_id))