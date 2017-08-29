import os
import tempfile
import json

from riseml.configs import load_config
from riseml.client import AdminApi, ApiClient
from riseml.consts import API_URL
from riseml.util import bytes_to_gib, print_table, TableRowDelimiter, call_api
from riseml.client import DefaultApi, ApiClient
from riseml.user import get_user
from riseml.project import push_project


PROJECT_NAME = 'smoke-test'

CONFIG = 'project: %s' % PROJECT_NAME
CONFIG += """
train:
    image:
        name: ubuntu:16.04
        install:
        - apt-get -y update
        - apt-get -y install stress fortune
    resources:
        cpus: 1
        mem: 1024
        gpus: 0
    run: 
    - bash stress.sh
"""

SCRIPT = """#!/bin/bash

for i in {1..100}
 do
  stress -c 1 -t 5
 for i in {1..100}
  do
    /usr/games/fortune
 done
 
 sleep 1
done
"""


def prepare_project_dir():
    dir = tempfile.mkdtemp()
    config_path = os.path.join(dir, 'riseml.yml')
    with open(config_path, 'w') as f:
        f.write(CONFIG)
    with open(os.path.join(dir, 'stress.sh'), 'w') as f:
        f.write(SCRIPT)
    return config_path


def add_system_test_parser(subparsers):
    parser = subparsers.add_parser('test', help="perform cluster tests")
    parser.add_argument('--nodename', help="the node name to schedule PODs on", 
                        required=False)
    parser.add_argument('--num_jobs', help="the number of jobs to run", default=1, 
                        type=int, required=False)   
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=API_URL)
    client = AdminApi(api_client)
    user = get_user()
    for i in range(args.num_jobs):
        print('Starting job %s of %s' % (i, args.num_jobs))
        start_job(user, args.nodename)


def start_job(user, nodename):
    config_path = prepare_project_dir()
    config = load_config(config_path)
    revision = push_project(user, PROJECT_NAME, config_path)
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)

    experiment = call_api(lambda: client.create_experiment(
        PROJECT_NAME, revision,
        kind='train', config=json.dumps(config.train.as_dict())
    ))