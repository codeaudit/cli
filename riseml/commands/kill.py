from riseml.client import DefaultApi, ApiClient

from riseml.client_config import get_api_url
from riseml.errors import handle_error

from riseml.util import call_api, is_experiment_id

def add_kill_parser(subparsers):
    parser = subparsers.add_parser('kill', help="kill on-going experiment or experiment series")
    parser.add_argument('ids', help="experiment/series identifiers (optional)", nargs='*')
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=get_api_url())
    client = DefaultApi(api_client)

    if args.ids:
        if any(not is_experiment_id(experiment_id) for experiment_id in args.ids):
            handle_error("Can only kill experiments!")
        for experiment_id in args.ids:
            kill_experiment(client, experiment_id)
    else:
        experiments = call_api(lambda: client.get_experiments())

        if not experiments:
            handle_error('No experiments to kill!')

        if experiments[0].state in ('FINISHED', 'FAILED', 'KILLED'):
            handle_error('No experiments to kill!')

        kill_experiment(client, experiments[0].id)
        

def kill_experiment(client, experiment_id):
    experiment = call_api(lambda: client.kill_experiment(experiment_id),
                          not_found=lambda: handle_error("Could not find experiment!"))
    if experiment.children:
        print("killed series {}".format(experiment.short_id))
    else:
        print("killed experiment {}".format(experiment.short_id))