from riseml.client import AdminApi, ApiClient
from riseml.util import call_api
from .system_info import add_system_info_parser
from .system_test import add_system_test_parser

def add_system_parser(subparsers):
    parser = subparsers.add_parser('system', help="system level commands")
    subsubparsers = parser.add_subparsers()
    add_system_register_parser(subsubparsers)    
    add_system_info_parser(subsubparsers)
    add_system_test_parser(subsubparsers)
    def run(args):
        parser.print_usage()
    parser.set_defaults(run=run)


def add_system_register_parser(subparsers):
    parser = subparsers.add_parser('register', help="register cluster with account")
    parser.set_defaults(run=run_register)


def run_register(args):
    print('Please enter the account key you would like to set: ')
    account_key = input('--> ').strip()
    api_client = ApiClient()
    client = AdminApi(api_client)
    call_api(lambda: client.update_or_create_cluster_info({'account_key': account_key}))        
    print("Account key set to: %s" % account_key)