from riseml.client import DefaultApi, ApiClient
from riseml.client.rest import ApiException

from riseml.errors import handle_http_error
from riseml.stream import stream_job_log


def run_job(project_name, revision, kind, config):
    api_client = ApiClient()
    client = DefaultApi(api_client)

    try:
        jobs = client.create_job(project_name, revision,
                                 kind=kind, config=config)
    except ApiException as e:
        handle_http_error(e.body, e.status)

    stream_job_log(jobs[0])
