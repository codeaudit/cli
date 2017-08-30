import os
import tempfile
import json
import math
import random
import shutil

from riseml.configs import load_config
from riseml.client import AdminApi, ApiClient
from riseml.consts import API_URL
from riseml.util import bytes_to_gib, print_table, TableRowDelimiter, call_api
from riseml.client import DefaultApi, ApiClient
from riseml.user import get_user
from riseml.project import push_project


PROJECT_NAME = 'smoke-test'

JOB_CONFIG = """project: {project_name}
train:
    image:
        name: ubuntu:16.04
        install:
        - apt-get -y update {more_steps}
        - apt-get -y install stress fortune
    resources:
        cpus: {num_cpus:.2f}
        mem: {memory}
        gpus: 0
    run: 
    - bash stress.sh
"""

SCRIPT = """#!/bin/bash
for i in $(seq 15)
do
stress --cpu {threads_cpu} --vm {threads_mem} --vm-bytes {mem_per_thread}M -t 20
for i in $(seq 100)
    do
        /usr/games/fortune
    done
sleep 1
done
"""


def get_job_config(num_cpus, memory, force_build_steps):
    more_steps = ''
    if force_build_steps:
        rand = random.randint(0, 10000)
        more_steps = ('&& echo %s && '
                       'apt-get -y install python-pip python-dev && '
                       'pip install --no-binary numpy scipy') % rand
    return JOB_CONFIG.format(num_cpus=num_cpus, memory=memory, 
                             project_name=PROJECT_NAME, more_steps=more_steps)


def get_script(num_cpus, memory):
    num_treads = math.ceil(num_cpus)
    mem_per_thread = int(math.floor(float(memory) / num_treads))
    return SCRIPT.format(threads_cpu=num_treads, threads_mem=num_treads,
                         mem_per_thread=mem_per_thread)



def prepare_project_dir(job_config, stress_script):
    dir = tempfile.mkdtemp()
    config_path = os.path.join(dir, 'riseml.yml')
    with open(config_path, 'w') as f:
        f.write(job_config)
    with open(os.path.join(dir, 'stress.sh'), 'w') as f:
        f.write(stress_script)
    return config_path


def remove_project_dir(config_path):
    shutil.rmtree(os.path.dirname(config_path))


def add_system_test_parser(subparsers):
    parser = subparsers.add_parser('test', help="perform cluster tests")
    parser.add_argument('--nodename', help="the node's hostname to schedule jobs on", 
                        required=False)
    parser.add_argument('--num_jobs', help="the number of jobs to run", default=1, 
                        type=int, required=False)
    parser.add_argument('--num_cpus', help="cpus per job to stress", default=1, 
                        type=float, required=False)
    parser.add_argument('--request_cpus', help="cpus per job to request", default=.1, 
                        type=float, required=False)
    parser.add_argument('--request_mem', help="mem per job to request", default=128, 
                        type=int, required=False)
    parser.add_argument('--mem', help="memory per job to stress", default=1024, 
                        type=int, required=False)  
    parser.add_argument('--force_build_steps', help="cause each job to perform considerable build steps",
                         action="store_const", const=True)
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=API_URL)
    client = AdminApi(api_client)
    user = get_user()
    
    for i in range(args.num_jobs):
        job_config = get_job_config(args.request_cpus, args.request_mem, args.force_build_steps)
        stress_script = get_script(args.num_cpus, args.mem)
        if i == 0:
            print('Job configuration:\n\n%s' % job_config)
        print('Starting job %s of %s to stress %s CPUs and %s MB of memory.' %
              (i + 1, args.num_jobs, args.num_cpus, args.mem))
        start_job(user, args.nodename, job_config, stress_script)


def start_job(user, nodename, job_config, stress_script):
    config_path = prepare_project_dir(job_config, stress_script)
    config = load_config(config_path)
    revision = push_project(user, PROJECT_NAME, config_path)
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)
    node_selector = ''
    if nodename:
        node_selector = 'kubernetes.io/hostname=%s' % nodename
    experiment = call_api(lambda: client.create_experiment(
        PROJECT_NAME, revision,
        kind='train', config=json.dumps(config.train.as_dict()),
        node_selectors=node_selector
    ))
    remove_project_dir(config_path)
