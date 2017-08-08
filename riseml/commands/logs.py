from riseml.client import DefaultApi, ApiClient
from riseml.client.rest import ApiException

from riseml.consts import API_URL, DEFAULT_CONFIG_NAME
from riseml.errors import handle_error, handle_http_error
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
        try:
            training = client.get_training(training_id)
        except ApiException as e:
            handle_http_error(e.body, e.status)
    else:
        try:
            trainings = client.get_trainings()
        except ApiException as e:
            handle_http_error(e.body, e.status)

        if not trainings:
            handle_error('No training logs to show')
            return

        training = trainings[0]
        experiment_id = None

    stream_training_log(training, experiment_id)
