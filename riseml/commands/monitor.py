from riseml.client import DefaultApi, ApiClient
from riseml.client.rest import ApiException

from riseml.util import call_api, is_job_id, is_experiment_id
from riseml.errors import handle_error, handle_http_error
from riseml.monitor import monitor_jobs


def add_monitor_parser(subparsers):
    parser = subparsers.add_parser('monitor', help="show monitor")
    parser.add_argument('id', help="experiment or job identifier (optional)", nargs='?')
    parser.add_argument('-g', '--gpu', help="detailed gpu stats", action="store_const", const=True)
    parser.set_defaults(run=run)


def get_experiment_jobs(experiment, roles=('train', 'dist-tf-master', 
                                           'dist-tf-ps', 'dist-tf-worker')):
   jobs = [j for j in experiment.jobs if j.role in roles]
   for c in experiment.children:
       jobs += get_experiment_jobs(c)
   return jobs


def run(args):
    api_client = ApiClient()
    client = DefaultApi(api_client)

    if args.id:
        if is_experiment_id(args.id):
            experiment = call_api(lambda: client.get_experiment(args.id),
                                  not_found=lambda: handle_error("Could not find experiment %s" % args.id))
            jobs = get_experiment_jobs(experiment)
            if not jobs:
                handle_error('Experiment has no jobs.')
            monitor_jobs(jobs, detailed=args.gpu, 
                         stream_meta={"experiment_id": experiment.short_id})
        elif is_job_id(args.id):
            job = call_api(lambda: client.get_job(args.id))
            monitor_jobs([job], detailed=args.gpu, stream_meta={"job_id": job.short_id})
        else:
            handle_error("Id is neither an experiment id nor a job id!")

    else:
        experiments = call_api(lambda: client.get_experiments())
        if not experiments:
            handle_error('No experiment logs to show!')
        experiment = call_api(lambda: client.get_experiment(experiments[0].short_id))
        jobs = get_experiment_jobs(experiment)
        if not jobs:
            handle_error('Last experiment has no jobs.')
        monitor_jobs(jobs, detailed=args.gpu, 
                     stream_meta={"experiment_id": experiments[0].short_id})
