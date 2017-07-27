from riseml.client import DefaultApi, ApiClient
from riseml.consts import API_URL


def get_user():
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)
    user = client.get_user()[0]
    return user