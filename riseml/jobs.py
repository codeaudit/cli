import json

from riseml.client import DefaultApi, ApiClient
from riseml.client.rest import ApiException

from riseml.errors import handle_error
from riseml.stream import stream_job_log
from riseml.consts import API_URL


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
