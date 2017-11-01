import re
import sys
import subprocess

import time
from urllib3.exceptions import HTTPError

from riseml.errors import handle_error
from riseml.client import AdminApi, ApiClient
from riseml.client.rest import ApiException
from riseml.client_config import get_api_url, get_api_key, write_config
from riseml.util import call_api, print_table, TableRowDelimiter, get_rsync_path
from riseml.client import Configuration
from riseml.user import get_user


def add_user_parser(parser):
    subparser = parser.add_parser('user', help="modify users")
    subsubparsers = subparser.add_subparsers()
    add_create_parser(subsubparsers)
    add_disable_parser(subsubparsers)
    add_list_parser(subsubparsers)
    add_display_parser(subsubparsers)
    add_login_parser(subsubparsers)
    def run(args):
        subparser.print_usage()
    subparser.set_defaults(run=run)


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


def add_login_parser(subparsers):
    parser = subparsers.add_parser('login', help="login new user")
    parser.add_argument('--api-host', help="DNS or IP/PORT of RiseML API server")
    parser.add_argument('--sync-host', help="DNS or IP/PORT of RiseML sync server")
    parser.add_argument('--api-key', help="Riseml API key")
    parser.set_defaults(run=run_login)


def run_login(args):
    print('Configuring new user login. This may overwrite existing configuration. \n')
    try:
        api_key, api_host, cluster_id = login_api(args)
        print()

        rsync_host = login_rsync(args)
        print()

        write_config(api_key, api_host, rsync_host, cluster_id)
        print('Login succeeded, config updated.')
    except KeyboardInterrupt as e:
        print('Aborting login. Configuration unchanged.')
        sys. exit(1)


def login_api(args):
    api_host = args.api_host
    if not args.api_host:
        print('Please provide the DNS name or IP of your RiseML API server.')
        print('Examples: 54.131.125.42, 54.131.125.42:31213')
        api_host = input('--> ').strip()
        print()
  
    api_key = args.api_key
    if not args.api_key:
        print('Please provide your API key.')
        print('Example: krlo2oxrtd2084zs7jahwyqu12b7mozg')
        api_key = input('--> ').strip()
        print()

    cluster_id = check_api_config(get_api_url(api_host), api_key)
    return api_key, api_host, cluster_id


def login_rsync(args):
    rsync_host = args.sync_host
    if not args.sync_host:
        print('Please provide the DNS name or IP of your RiseML sync server.')
        print('Examples: 54.131.125.43, 54.131.125.42:31876')
        rsync_host = input('--> ').strip()
        print()

    check_sync_config('rsync://%s/sync' % rsync_host)
    return rsync_host


def check_sync_config(rsync_url, timeout=20):
    print('Waiting %ss for connection to sync server %s ...' % (timeout, rsync_url))
    
    start = time.time()
    while True:
        sync_cmd = [get_rsync_path(),
                '--dry-run',
                '--timeout=5',
                '--contimeout=5',
                '.',
                rsync_url]
        proc = subprocess.Popen(sync_cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)    
        res = proc.wait()
        if res != 0:
            if time.time() - start < timeout:
                time.sleep(1)
                continue
            else:
                handle_error('Could not connect to sync server: %s' % proc.stdout.read().decode('utf-8'))
        else:
            print('Success!')
            break


def check_api_config(api_url, api_key, timeout=180):
    print('Waiting %ss for successful login to %s with API key \'%s\' ...' % (timeout, api_url, api_key))
    config = Configuration()
    old_api_host = config.host
    old_api_key = config.api_key['api_key']
    config.host = api_url
    config.api_key['api_key'] = api_key
    api_client = ApiClient()
    client = AdminApi(api_client)
    start = time.time()
    while True:
        try:
            cluster_infos = client.get_cluster_infos()
            cluster_id = get_cluster_id(cluster_infos)
            print('Success! Cluster ID: %s' % cluster_id)
            config.api_key['api_key'] = old_api_key
            config.host = old_api_host
            return cluster_id
        except ApiException as exc:
            if exc.reason == 'UNAUTHORIZED':
                print(exc.status, 'Unauthorized - wrong api key?')
                sys.exit(1)
            elif time.time() - start < timeout:
                time.sleep(1)
                continue
            else:
                print(exc.status, exc.reason)
                sys.exit(1)
        except HTTPError as e:
            if time.time() - start < timeout:
                time.sleep(1)
                continue
            else:
                print('Unable to connecto to %s ' % api_url)
                # all uncaught http errors goes here
                print(e.reason)
                sys.exit(1)


def get_cluster_id(cluster_infos):
    for ci in cluster_infos:
        if ci.key == 'cluster_id':
            return ci.value


def run_create(args):
    api_client = ApiClient()
    client = AdminApi(api_client)
    validate_username(args.username)
    validate_email(args.email)
    user = call_api(lambda: client.update_or_create_user(username=args.username, email=args.email))[0]
    print('Created user %s' % user.username)
    print(' email: %s' % user.email)
    print(' api_key: %s' % user.api_key_plaintext)


def run_list(args):
    api_client = ApiClient()
    client = AdminApi(api_client)
    users = call_api(lambda: client.get_users())
    rows = []
    for u in users:
        rows.append([u.username, u.email, str(u.is_enabled)])

    print_table(
        header=['Username', 'Email', 'Enabled'],
        min_widths=[12, 6, 9],
        column_spaces=2,
        rows=rows
    )


def run_display(args):
    api_client = ApiClient()
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
        choice = input()
    except KeyboardInterrupt:
        user_exit()
    if choice.strip() != 'y':
        user_exit()
    api_client = ApiClient()
    client = AdminApi(api_client)
    call_api(lambda: client.delete_user(username=args.username))
    print('User %s disabled.' % args.username)


def validate_username(username):
    if not re.match(r'^[A-Za-z0-9]+-?[A-Za-z0-9]+$', username):
        handle_error('Username must only contain alphanumeric characters with at most a single enclosed hyphen')

def validate_email(email):
    if '@' not in email:
        handle_error('Invalid email')
    