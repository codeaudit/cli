from riseml.client import DefaultApi, ApiClient
from riseml.client.rest import ApiException

from riseml.util import call_api
from riseml.consts import API_URL
from riseml.errors import handle_error, handle_http_error
from riseml.stream import stream_training_log


def add_logs_parser(subparsers):
    parser = subparsers.add_parser('logs', help="show logs")
    parser.add_argument('experiment', help="experiment identifier (optional)", nargs='?')
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)

    if args.experiment:
        training_id, _, experiment_id = args.experiment.partition('.')
        training = call_api(lambda: client.get_training(training_id))
    else:
        trainings = call_api(lambda: client.get_trainings())

        if not trainings:
            handle_error('No training logs to show')

        training = trainings[0]
        experiment_id = None

    stream_training_log(training, experiment_id)
