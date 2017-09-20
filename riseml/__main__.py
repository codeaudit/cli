# -*- coding: utf-8 -*-
import sys
import os
import argparse
import rollbar
import codecs
import sys

from urllib3.exceptions import HTTPError

from riseml.commands import *
from riseml.consts import API_URL, STREAM_URL, GIT_URL, USER_URL, ROLLBAR_ENDPOINT, CLUSTER_ID, ENVIRONMENT, VERSION
from riseml.errors import handle_error

import logging
logging.getLogger('urllib3.connectionpool').setLevel(logging.ERROR)
sys.stderr = codecs.EncodedFile(sys.stderr, file_encoding='utf-8')
sys.stdout = codecs.EncodedFile(sys.stdout, file_encoding='utf-8')



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', help="show endpoints", action='store_const', const=True)
    parser.add_argument('--version', '-V', help="show version", action='version', version='RiseML {}'.format(VERSION))

    subparsers = parser.add_subparsers()

    # user ops
    add_whoami_parser(subparsers)

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
