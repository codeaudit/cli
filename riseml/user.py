from riseml.client import DefaultApi, ApiClient
from riseml.util import call_api


def get_user():
    api_client = ApiClient()
    client = DefaultApi(api_client)

    user = call_api(lambda: client.get_user())[0]

    return user