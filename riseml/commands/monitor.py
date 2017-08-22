from riseml.client import DefaultApi, ApiClient
from riseml.client.rest import ApiException

from riseml.util import call_api, is_job_id, is_experiment_id
from riseml.consts import API_URL
from riseml.errors import handle_error, handle_http_error
from riseml.monitor import monitor_jobs


def add_monitor_parser(subparsers):
    parser = subparsers.add_parser('monitor', help="show monitor")
    parser.add_argument('id', help="experiment or job identifier (optional)", nargs='?')
    parser.add_argument('-l', '--long', help="detailed job stats", action="store_const", const=True)
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)

    if args.id:
        if is_experiment_id(args.id):
            experiment = call_api(lambda: client.get_experiment(args.id))
            monitor_jobs(experiment.jobs, detailed=args.long, 
                         stream_meta={"experiment_id": experiment.short_id})
        elif is_job_id(args.id):
            job = call_api(lambda: client.get_job(args.id))
            monitor_jobs([job], detailed=args.long, stream_meta={"job_id": job.short_id})
        else:
            handle_error("Id is neither an experiment id nor a job id!")

    else:
        experiments = call_api(lambda: client.get_experiments())
        if not experiments:
            handle_error('No experiment logs to show!')
        monitor_jobs(experiments[0].jobs, detailed=args.long, 
                     stream_meta={"experiment_id": experiment.short_id})
