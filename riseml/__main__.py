# -*- coding: utf-8 -*-
import sys
import argparse

from riseml.commands import *
from riseml.consts import API_URL, STREAM_URL, GIT_URL, USER_URL


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
        args.run(args)
    else:
        parser.print_usage()

if __name__ == '__main__':
    main()
