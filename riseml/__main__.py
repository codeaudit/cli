# -*- coding: utf-8 -*-
import sys
import os
import argparse
import rollbar
import sys

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
    else:
        parser.print_usage()


def entrypoint():
    if get_environment() not in ['development', 'test']:
        if not get_cluster_id():
            handle_error("RiseML cluster ID ist not available")
        rollbar.init(
            get_cluster_id(), # Use cluster id as access token
            get_environment(),
            endpoint=get_rollbar_endpoint(),
            root=os.path.dirname(os.path.realpath(__file__)))
        try:
            main()
        except Exception:
            rollbar.report_exc_info()
            handle_error("An unexpected error occured. A report was sent to RiseML successfully.")
    else:
        main()


if __name__ == '__main__':

    entrypoint()
