import json

from riseml.client import AdminApi, ApiClient
from riseml.client.rest import ApiException


def add_register_parser(subparsers):
    parser = subparsers.add_parser('register', help="register user (only admin)")
    parser.add_argument('--username', help="a person's username", required=True)
    parser.add_argument('--email', help="a person's email", required=True)
    parser.set_defaults(run=run)

def run(args):
    api_client = ApiClient(host=api_url)
    client = AdminApi(api_client)
    user = None
    try:
        user = client.update_or_create_user(username=args.username, email=args.email)[0]
    except ApiException as e:
        body = json.loads(e.body)
        handle_error(body['message'], e.status)
    print(user)