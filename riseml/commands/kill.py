from riseml.client import DefaultApi, ApiClient

from riseml.consts import API_URL
from riseml.errors import handle_error

from riseml.util import call_api

def add_kill_parser(subparsers):
    parser = subparsers.add_parser('kill', help="kill on-going experiment or experiment series")
    parser.add_argument('experiments', help="experiment/series identifier (optional)", nargs='*')
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)

    experiments = args.experiments

    if not experiments:
        experiments = call_api(lambda: client.get_experiments())

        if not experiments:
            handle_error('No experiments to kill')

        if experiments[0].state in ('FINISHED', 'FAILED', 'KILLED'):
            handle_error('No experiments to kill')

        experiments = [experiments[0].id]

    for experiment_id in experiments:
        experiment = call_api(lambda: client.kill_experiment(experiment_id))

        if experiment.children:
            print("killed series {}".format(experiment.short_id))
        else:
            print("killed experiment {}".format(experiment.short_id))
