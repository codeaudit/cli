from riseml.client import DefaultApi, ApiClient
from riseml.client.rest import ApiException

from riseml.errors import handle_http_error
from riseml.consts import API_URL


def get_user():
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)

    try:
        user = client.get_user()[0]
    except ApiException as e:
        handle_http_error(e.body, e.status)

    return user