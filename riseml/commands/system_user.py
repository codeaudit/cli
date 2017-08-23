import sys
from riseml.client import AdminApi, ApiClient
from riseml.consts import API_URL
from riseml.util import call_api, print_table, TableRowDelimiter


def add_system_user_parser(subparsers):
    parser = subparsers.add_parser('user', help="modify users")
    subsubparsers = parser.add_subparsers()
    add_create_parser(subsubparsers)
    add_disable_parser(subsubparsers)
    add_list_parser(subsubparsers)
    add_display_parser(subsubparsers)


def add_create_parser(subparsers):
    parser = subparsers.add_parser('create', help="create user")
    parser.add_argument('--username', help="a person's username", required=True)
    parser.add_argument('--email', help="a person's email", required=True)
    parser.set_defaults(run=run_create)


def add_disable_parser(subparsers):
    parser = subparsers.add_parser('disable', help="disable user")
    parser.add_argument('username', help="a person's username")
    parser.set_defaults(run=run_disable)


def add_display_parser(subparsers):
    parser = subparsers.add_parser('display', help="show user info")
    parser.add_argument('username', help="a person's username")
    parser.set_defaults(run=run_display)


def add_list_parser(subparsers):
    parser = subparsers.add_parser('list', help="list users")
    parser.set_defaults(run=run_list)


def run_create(args):
    api_client = ApiClient(host=API_URL)
    client = AdminApi(api_client)

    user = call_api(lambda: client.update_or_create_user(username=args.username, email=args.email))[0]

    print('Created user %s' % user.username)
    print(' email: %s' % user.email)
    print(' api_key: %s' % user.api_key_plaintext)


def run_list(args):
    api_client = ApiClient(host=API_URL)
    client = AdminApi(api_client)
    users = call_api(lambda: client.get_users())
    rows = []
    for u in users:
        rows.append([u.username, u.email, str(u.is_enabled)])

    print_table(
        header=['Username', 'Email', 'Enabled'],
        min_widths=[18, 6, 9, 4],
        rows=rows
    )


def run_display(args):
    api_client = ApiClient(host=API_URL)
    client = AdminApi(api_client)
    users = call_api(lambda: client.get_users(username=args.username))
    if not users:
        print('User %s not found.' % args.username)
    else:
        user = users[0]
        print('username: %s' % user.username)
        print('email: %s' % user.email)
        print('api_key: %s' % user.api_key_plaintext)


def run_disable(args):
    sys.stdout.write("Are you sure you want to disable user %s? [y/n]: " % args.username)
    def user_exit():
        print("Apparently not...")
        exit(0)
    try:
        choice = raw_input()
    except KeyboardInterrupt:
        user_exit()
    if choice.strip() != 'y':
        user_exit()
    api_client = ApiClient(host=API_URL)
    client = AdminApi(api_client)
    call_api(lambda: client.delete_user(username=args.username))
    print('User %s disabled.' % args.username)