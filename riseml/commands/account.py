import webbrowser
import requests
import sys

from riseml.client import AdminApi, ApiClient
from riseml.util import call_api, browser_available, bold, read_yes_no
from riseml.client_config import get_riseml_url


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
        register_url = get_riseml_url() + 'upgrade/%s' % account.key
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
    def readable_features(features):
        names = {'user_management': 'User Management'}
        return [names.get(f, f) for f in features]

    api_client = ApiClient()
    client = AdminApi(api_client)
    account = call_api(lambda: client.get_account_info())


    if account.name is None:
        print('You have not registered with an account. '
              'Please run ' + bold('riseml account register'))
    else:
        backend_info = get_account_info_backend(account.key)
        print('Name: %s' % account.name)
        print('Key:  %s' % account.key)
        upgrade_text = ''
        plan = backend_info['plan']
        if plan == 'basic':
            upgrade_text = ' (run ' + bold('riseml account upgrade') + ' to switch)'
        print('Plan: %s%s' % (plan.title(), upgrade_text))
        for feature in readable_features(account.enabled_features):
            print('      - %s' % feature)


def run_register(args):
    api_client = ApiClient()
    client = AdminApi(api_client)
    account = call_api(lambda: client.get_account_info())
    if account.key is not None:
        print('Note: this cluster is already registered with an account. '
              'You can continue and register with another account.')
        read_and_register_account_key()
    else:
        key_exists = read_yes_no('Do you already have an account key')
        if key_exists:
            read_and_register_account_key()
        else:
            register_url = get_riseml_url() + 'register/basic/%s' % account.cluster_id
            if browser_available():
                webbrowser.open_new_tab(register_url)
            else:
                print('Please visit this URL and follow instructions'
                    ' to register an account: %s' % register_url)
            read_and_register_account_key()


def read_and_register_account_key():
    account_key = input('Please enter your account key: ').strip()
    api_client = ApiClient()
    client = AdminApi(api_client)
    res = call_api(lambda: client.update_account(account_key=account_key))
    if res.name is None:
        print('Invalid account key. Please verify that your key is correct '
              'or ask for support via contact@riseml.com. '
              'Your cluster is not registered with an account.')
    else:
        print('Registered succesfully! Account name: %s' % res.name)


def get_account_info_backend(account_key):
    url = get_riseml_url() + 'backend/accounts/%s' % account_key
    try:
        res = requests.get(url)
        res.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Couldn't obtain account information from RiseML.")
        sys.exit(1)
    return res.json()
