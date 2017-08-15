# -*- coding: utf-8 -*-
import sys
import os
import argparse
import rollbar

from urllib3.exceptions import HTTPError

from riseml.commands import *
from riseml.consts import API_URL, STREAM_URL, GIT_URL, USER_URL, ROLLBAR_ENDPOINT, CLUSTER_ID, ENVIRONMENT
from riseml.errors import handle_error

import logging
logging.getLogger('urllib3.connectionpool').setLevel(logging.ERROR)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', help="show endpoints",
                        action='store_const', const=True)

    subparsers = parser.add_subparsers()

    # user ops
    add_register_parser(subparsers)
    add_whoami_parser(subparsers)

    # clusterinfo ops
    add_cluster_parser(subparsers)

    # worklow ops
    add_init_parser(subparsers)
    add_train_parser(subparsers)
    add_exec_parser(subparsers)
    add_deploy_parser(subparsers)
    add_logs_parser(subparsers)
    add_kill_parser(subparsers)
    add_status_parser(subparsers)

    args = parser.parse_args(sys.argv[1:])

    if args.v:
        print('api_url: %s' % API_URL)
        print('stream_url: %s' % STREAM_URL)
        # print('RISEML_SCRATCH_ENDPOINT: %s' % scratch_url)
        print('git_url: %s' % GIT_URL)
        print('user_url: %s' % USER_URL)

    if hasattr(args, 'run'):
        try:
            args.run(args)
        except HTTPError as e:
            # all uncaught http errors goes here
            handle_error(e.message)
    else:
        parser.print_usage()

def entrypoint():
    if ENVIRONMENT not in ['development', 'test']:
        if not CLUSTER_ID:
            handle_error("Environment variable RISEML_CLUSTER_ID has to be set!")
        rollbar.init(
            CLUSTER_ID, # Use cluster id as access token
            ENVIRONMENT,
            endpoint=ROLLBAR_ENDPOINT,
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
