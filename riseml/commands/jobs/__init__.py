import json

from riseml.client import DefaultApi, ApiClient
from riseml.client.rest import ApiException

from riseml import util
from riseml.errors import handle_error
from riseml.stream import stream_log
from riseml.consts import STREAM_URL, API_URL


def run_job(project_name, revision, kind, config):
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)

    try:
        jobs = client.create_job(project_name, revision,
                                 kind=kind, config=config)
    except ApiException as e:
        body = json.loads(e.body)
        handle_error(body['message'], e.status)

    stream_job_log(jobs[0])


def stream_job_log(job):
    def flatten_jobs(job):
        for c in job.children:
            for j in flatten_jobs(c):
                yield j
        yield job

    jobs = list(flatten_jobs(job))
    ids_to_name = {job.id: util.get_job_name(job) for job in jobs}
    url = '%s/ws/jobs/%s/stream' % (STREAM_URL, job.id)
    stream_log(url, ids_to_name)


def stream_training_log(training):
    url = '%s/ws/trainings/%s/stream' % (STREAM_URL, training.id)
    ids_to_name = {}
    ids_to_name[training.id] = '{}'.format(training.short_id)
    if len(training.experiments) == 1:
        for job in training.experiments[0].jobs:
            ids_to_name[job.id] = '{}: {}'.format(training.short_id, job.name)
    else:
        for experiment in training.experiments:
            ids_to_name[experiment.id] = '{}.{}'.format(training.short_id, experiment.number)
            for job in experiment.jobs:
                ids_to_name[job.id] = '{}.{}: {}'.format(training.short_id, experiment.number, job.name)

    for job in training.jobs:
        if job.id not in ids_to_name:
            ids_to_name[job.id] = '{}: {}'.format(training.short_id, job.name)

    stream_log(url, ids_to_name)
