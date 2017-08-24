from riseml.client import DefaultApi, ApiClient

from riseml.util import call_api, is_job_id, is_experiment_id
from riseml.consts import API_URL
from riseml.errors import handle_error
from riseml.stream import stream_experiment_log, stream_job_log


def add_logs_parser(subparsers):
    parser = subparsers.add_parser('logs', help="show logs")
    parser.add_argument('id', help="experiment or job identifier (optional)", nargs='?')
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)

    if args.id:
        if is_experiment_id(args.id):
            experiment = call_api(lambda: client.get_experiment(args.id),
                                  not_found=lambda: handle_error("Could not find experiment!"))
            stream_experiment_log(experiment)
        elif is_job_id(args.id):
            job = call_api(lambda: client.get_job(args.id),
                           not_found=lambda: handle_error("Could not find job!"))
            stream_job_log(job)
        else:
            handle_error("Can only show logs for jobs or experiments!")

    else:
        experiments = call_api(lambda: client.get_experiments())
        if not experiments:
            handle_error('No experiment logs to show!')
        stream_experiment_log(experiments[0])
