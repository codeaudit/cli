import json

from .. import util

from riseml.client import DefaultApi, ApiClient
from riseml.client.rest import ApiException

from ..push import push_project

def add_train_parser(subparsers):
    parser = subparsers.add_parser('train', help="run new experiment or experiment series")
    parser.add_argument('-f', '--config-file', help="config file to use", type=str, default='riseml.yml')
    parser.set_defaults(run=run)


def run(args):
    project_name = get_project_name()
    # TODO: validate config here already
    config_section = load_config(args.config_file, 'train')
    user = get_user()
    revision = push_project(user, project_name)
    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)
    try:
        training = client.create_training(project_name, revision, kind='train', config=json.dumps(config_section))
    except ApiException as e:
        body = json.loads(e.body)
        handle_error(body['message'], e.status)
    stream_training_log(training)


def stream_job_log(job):
    def flatten_jobs(job):
        for c in job.children:
            for j in flatten_jobs(c):
                yield j
        yield job

    jobs = list(flatten_jobs(job))
    ids_to_name = {job.id: util.get_job_name(job) for job in jobs}
    url = '%s/ws/jobs/%s/stream' % (stream_url, job.id)
    stream_log(url, ids_to_name)


def stream_training_log(training):
    url = '%s/ws/trainings/%s/stream' % (stream_url, training.id)
    ids_to_name = {}
    ids_to_name[training.id] = 'training'
    for experiment in training.experiments:
        ids_to_name[experiment.id] = 'exp. {}'.format(experiment.number)
        for job in experiment.jobs:
            ids_to_name[job.id] = 'exp. {}: {}'.format(experiment.number, job.name)
    for job in training.jobs:
        if job.id not in ids_to_name:
            ids_to_name[job.id] = job.name
    stream_log(url, ids_to_name)