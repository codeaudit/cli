# -*- coding: utf-8 -*-
import sys
import os
import argparse
import builtins
import rollbar

from urllib3.exceptions import HTTPError

from riseml.commands import *
from riseml.client_config import get_api_url, get_stream_url, get_sync_url, get_git_url, get_environment, get_cluster_id, get_rollbar_endpoint
from riseml.consts import VERSION
from riseml.errors import handle_error

import logging
logging.getLogger('urllib3.connectionpool').setLevel(logging.ERROR)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', help="show endpoints", action='store_const', const=True)
    parser.add_argument('--version', '-V', help="show version", action='version', version='RiseML CLI {}'.format(VERSION))
    subparsers = parser.add_subparsers()

    # user ops
    add_whoami_parser(subparsers)
    add_user_parser(subparsers)

    # system ops
    add_system_parser(subparsers)
    add_account_parser(subparsers)

    # worklow ops
    add_init_parser(subparsers)
    add_train_parser(subparsers)
    #add_exec_parser(subparsers)
    add_monitor_parser(subparsers)
    #add_deploy_parser(subparsers)
    add_logs_parser(subparsers)
    add_kill_parser(subparsers)
    add_status_parser(subparsers)

    args = parser.parse_args(sys.argv[1:])

    if args.v:
        print('api_url: %s' % get_api_url())
        print('sync_url: %s' % get_sync_url())
        print('stream_url: %s' % get_stream_url())
        print('git_url: %s' % get_git_url())

    if hasattr(args, 'run'):
        try:
            args.run(args)
        except HTTPError as e:
            # all uncaught http errors goes here
            handle_error(str(e))
        except KeyboardInterrupt:
            print('\nAborting...')
    else:
        parser.print_usage()
    
def safely_encoded_print(print_func):
    def convert_to_ascii(arg):
        if isinstance(arg, str):
            arg = arg.replace(u'\u25cb ', '').replace(u'\u25cf ', '')
            arg = arg.replace(u'\u2713 ', '').replace(u'\u2717 ', '')
            arg = arg.replace(u'├╴', '  ').replace(u'╰╴', '  ')
            return str.encode(arg, encoding='ascii', errors='replace').decode()
        else:
            return arg

    def wrapped_print_func(*args, **kwargs):
        try:
            return print_func(*args, **kwargs)
        except UnicodeEncodeError:
            converted_args = [convert_to_ascii(arg) for arg in args]
            return print_func(*converted_args, **kwargs)

    return wrapped_print_func

def entrypoint():
    builtins.print = safely_encoded_print(print)
    if get_environment() not in ['development', 'test']:
        cluster_id = get_cluster_id()
        rollbar.init(
            cluster_id if cluster_id else '00000000-0000-0000-0000-000000000000',
            get_environment(),
            endpoint=get_rollbar_endpoint(),
            root=os.path.dirname(os.path.realpath(__file__)))
        try:

            main()
        except Exception:
            rollbar.report_exc_info()
            handle_error("An unexpected error occured.")
    else:
        main()


if __name__ == '__main__':

    entrypoint()
