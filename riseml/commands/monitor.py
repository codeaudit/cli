from riseml.client import DefaultApi, ApiClient
from riseml.client.rest import ApiException

from riseml.util import call_api, is_job_id, is_experiment_id
from riseml.errors import handle_error, handle_http_error
from riseml.monitor import monitor_job, monitor_experiment


def add_monitor_parser(subparsers):
    parser = subparsers.add_parser('monitor', help="show monitor")
    parser.add_argument('id', help="experiment or job identifier (optional)", nargs='?')
    parser.add_argument('-g', '--gpu', help="detailed gpu stats", action="store_const", const=True)
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient()
    client = DefaultApi(api_client)

    if args.id:
        if is_experiment_id(args.id):
            experiment = call_api(lambda: client.get_experiment(args.id),
                                  not_found=lambda: handle_error("Could not find experiment %s" % args.id))
            monitor_experiment(experiment, detailed=args.gpu, 
                               stream_meta={"experiment_id": experiment.short_id})
        elif is_job_id(args.id):
            job = call_api(lambda: client.get_job(args.id),
                           not_found=lambda: handle_error("Could not find job!"))
            monitor_job(job, detailed=args.gpu)
        else:
            handle_error("Id is neither an experiment id nor a job id!")

    else:
        experiments = call_api(lambda: client.get_experiments())
        if not experiments:
            handle_error('No experiments to monitor!')
        experiment = call_api(lambda: client.get_experiment(experiments[0].short_id))
        monitor_experiment(experiment, detailed=args.gpu)
