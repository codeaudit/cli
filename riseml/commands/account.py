import webbrowser
import requests

from riseml.client import AdminApi, ApiClient
from riseml.util import call_api, browser_available, handle_http_error, handle_error, bold
from .system_info import add_system_info_parser
from .system_test import add_system_test_parser
from riseml.client_config import get_riseml_backend_url


def add_account_parser(subparsers):
    parser = subparsers.add_parser('account', help="account level commands")
    subsubparsers = parser.add_subparsers()
    add_account_upgrade_parser(subsubparsers)
    add_account_sync_parser(subsubparsers)
    add_account_register_parser(subsubparsers)
    add_account_info_parser(subsubparsers)
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


def add_account_info_parser(subparsers):
    parser = subparsers.add_parser('info', help="display your account info")
    parser.set_defaults(run=run_info)


def run_upgrade(args):
    api_client = ApiClient()
    client = AdminApi(api_client)
    account = call_api(lambda: client.get_account_info())
    if account.key is None:
        print('You have not registered with an account. '
              'Please run ' + bold('riseml account register'))
    else:
        register_url = get_riseml_backend_url() + 'upgrade?accounKey=%s' % account.key
        if browser_available():
            webbrowser.open_new_tab(register_url)
        else:
            print('Please visit this URL and follow instructions'
                ' to upgrade your account: %s' % register_url)


def run_sync(args):
    api_client = ApiClient()
    client = AdminApi(api_client)
    res = call_api(lambda: client.sync_account_info())
    if res.name is None:
        print('You have not registered with an account. '
              'Please run ' + bold('riseml account register'))
    else:
        print('Successfully synced account info.'
              ' Account name: %s' % res.name)


def run_info(args):
    api_client = ApiClient()
    client = AdminApi(api_client)
    account = call_api(lambda: client.get_account_info())
    if account.name is None:
        print('You have not registered with an account. '
              'Please run ' + bold('riseml account register'))
    else:
        print('Account name: %s' % account.name)
        print('Account key:  %s' % account.key)


def run_register(args):
    api_client = ApiClient()
    client = AdminApi(api_client)
    account = call_api(lambda: client.get_account_info())
    if account.key is not None:
        print('You have already registered with an account.')
    else:
        register_url = get_riseml_backend_url() + 'register'
        print('If you haven\'t registered your account yet, please go to the following'
            ' URL to get your account key:\n\n %s' % register_url)
        print('\nPlease enter your account key: ')
        account_key = input('--> ').strip()
        api_client = ApiClient()
        client = AdminApi(api_client)
        res = call_api(lambda: client.update_account(account_key=account_key))
        if res.name is None:
            print('Invalid account key. Please verify that your key is correct '
                  'or ask for support via contact@riseml.com')
        else:
            print('Registered succesfully! Account name: %s' % res.name)