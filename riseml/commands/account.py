import webbrowser
import requests

from riseml.client import AdminApi, ApiClient
from riseml.util import call_api, browser_available, handle_http_error, handle_error
from .system_info import add_system_info_parser
from .system_test import add_system_test_parser
from riseml.client_config import get_riseml_backend_url


def add_account_parser(subparsers):
    parser = subparsers.add_parser('account', help="account level commands")
    subsubparsers = parser.add_subparsers()
    add_account_upgrade_parser(subsubparsers)
    add_account_sync_parser(subsubparsers)
    add_account_register_parser(subsubparsers)
    def run(args):
        parser.print_usage()
    parser.set_defaults(run=run)


def add_account_register_parser(subparsers):
    parser = subparsers.add_parser('register', help="register your account")
    parser.set_defaults(run=run_register)


def add_account_upgrade_parser(subparsers):
    parser = subparsers.add_parser('upgrade', help="upgrade your account")
    parser.set_defaults(run=run_upgrade)


def add_account_sync_parser(subparsers):
    parser = subparsers.add_parser('sync', help="sync your account info")
    parser.set_defaults(run=run_sync)


def run_upgrade(args):
    cluster_id = get_cluster_infos().get('cluster_id')
    register_url = get_riseml_backend_url() + 'upgrade?clusterId=%s' % cluster_id
    if browser_available():
        webbrowser.open_new_tab(register_url)
    else:
        print('Please visit the this URL and follow the instructionss'
              ' to upgrade your account: %s' % register_url)


def run_sync(args):
    api_client = ApiClient()
    client = AdminApi(api_client)
    res = call_api(lambda: client.sync_account_info())
    print(res)


def run_register(args):
    print('Please enter the account key you would like to set: ')
    account_key = input('--> ').strip()
    api_client = ApiClient()
    client = AdminApi(api_client)
    res = call_api(lambda: client.update_account(account_key=account_key))
    print("Account %s registered" % res.name)


def get_cluster_infos():
    api_client = ApiClient()
    client = AdminApi(api_client)
    res = call_api(lambda: client.get_cluster_infos())
    return {r.key: r.value for r in res}
