from riseml.client import DefaultApi, ApiClient

from riseml.util import call_api
from riseml.consts import API_URL
from riseml.errors import handle_error
from riseml.stream import stream_experiment_log


def add_logs_parser(subparsers):
    parser = subparsers.add_parser('logs', help="show logs")
    parser.add_argument('experiment', help="experiment identifier (optional)", nargs='?')
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)

    if args.experiment:
        experiment = call_api(lambda: client.get_experiment(args.experiment))
    else:
        experiments = call_api(lambda: client.get_experiments())
        if not experiments:
            handle_error('No experiment logs to show')
        experiment = experiments[0]

    stream_experiment_log(experiment)
