# -*- coding: utf-8 -*-

from __future__ import print_function

import json

from riseml.client import DefaultApi, ApiClient

from riseml import util
from riseml.errors import handle_error
from riseml.consts import API_URL, ENDPOINT_URL


def add_status_parser(subparsers):
    parser = subparsers.add_parser('status', help="show (running) experiments")
    parser.add_argument('id', help='id of RiseML entity for which to show status', nargs='?')
    parser.add_argument('-a', '--all', help="show all experiments", action="store_const", const=True)
    parser.add_argument('-u', '--all-users', help="show experiments for all users (admin only)", action="store_const", const=True)
    parser.add_argument('-l', '--long', help="expand series", action="store_const", const=True)
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)

    if args.id and util.is_experiment_id(args.id):
        experiment = util.call_api(
            lambda: client.get_experiment(args.id),
            not_found=lambda: handle_error("Could not find experiment!")
        )
        if experiment.children:
            show_experiment_group(experiment)
        else:
            show_experiment(experiment)
    elif args.id and util.is_job_id(args.id):
        job = util.call_api(
            lambda: client.get_job(args.id),
            not_found=lambda: handle_error("Could not find job!")
        )
        show_job(job)
    elif args.id and util.is_user_id(args.id):
        show_experiments(client.get_experiments(user=args.id[1:]),
                         all=args.all, collapsed=not args.long, users=args.all_users)
    elif not args.id:
        show_experiments(client.get_experiments(all_users=args.all_users),
                         all=args.all, collapsed=not args.long, users=args.all_users)
    else:
        handle_error("Id does not identify any RiseML entity!")


def params(experiment):
    return ', '.join(['{}={}'.format(p, v) for p, v in json.loads(experiment.params).items()])


def show_dict(dictionary, indentation=2, title=None):
    if not dictionary:
        return
    if title:
        print(title)
    for attribute, value in dictionary.items():
        if isinstance(value, dict):
            show_dict(value, indentation=indentation + 2)
        elif value is not None:
            print("  {}: {}".format(attribute, value))

def show_common_header(entity, type):
    print("ID: {}".format(entity.short_id))
    print("Type: {}".format(type))
    print("State: {}".format(entity.state))

def show_job_table(jobs):
    rows = [
        ([job.short_id,
         job.state,
         util.get_since_str(job.started_at),
         util.get_since_str(job.finished_at),
         job.reason or '',
         job.message[:17] + '...' if job.message and len(job.message) > 20 else job.message or '',
         job.exit_code or '',
         'N/A', 'N/A', 'N/A']) for job in jobs
    ]

    util.print_table(
        header=['JOB ID', 'STATE', 'STARTED', 'FINISHED', 'REASON', 'MESSAGE', 'EXIT CODE', 'GPU', 'CPU', 'MEM'],
        min_widths=[13, 13, 13, 13, 13, 20, 10, 6, 6, 6],
        rows=rows
    )

def show_experiment(experiment):
    show_common_header(experiment, "Experiment")
    print("Image: {}".format(experiment.image))
    print("Framework: {}".format(experiment.framework))
    show_dict(experiment.framework_config.to_dict(), title="Framework Config:")
    
    if experiment.framework == 'tensorflow' and experiment.framework_config.tensorboard:
        tensorboard_job = next((job for job in experiment.jobs if job.role == 'tensorboard'), None)
        if tensorboard_job:
            print("Tensorboard: {}/{}".format(ENDPOINT_URL, tensorboard_job.service_name))

    print("Run Commands:")
    print(''.join(["  {}".format(command) for command in experiment.run_commands]))
    print("Concurrent Experiments: {}".format(experiment.concurrent_experiments))
    print("Params: {}\n".format(params(experiment)))

    show_job_table(experiment.jobs)

def show_job(job):
    show_common_header(job, "Job")
    print("Started: {} ago".format(util.get_since_str(job.started_at)))
    print("Finished: {} ago".format(util.get_since_str(job.finished_at)))
    if job.reason is not None:
        print("Reason: {}".format(job.reason))
    if job.message is not None:
        print("Message: {}".format(job.message))    
    if job.exit_code is not None:    
        print("Exit Code: {}".format(job.exit_code))
    print("Requested cpus: {}".format(job.cpus))
    print("Requested mem: {}".format(job.mem))
    print("Requested gpus: {}".format(job.gpus))
    print("Run Commands:")
    print(''.join(["  {}".format(command) for command in json.loads(job.commands)]))
    show_dict(json.loads(job.environment), title="Environment:")
    if job.state == 'FAILED':
        print("Reason: {}".format(job.reason))

def get_experiments_rows(group, with_project=True, with_type=True, with_params=True, indent=True):
    rows = []

    for i, experiment in enumerate(group.children):
        indent_str = (u'├╴' if i < len(group.children) - 1 else u'╰╴') if indent else ''
        values = [indent_str + experiment.short_id]

        if with_project:
            values += [experiment.changeset.repository.name]

        values += [experiment.state, util.get_since_str(experiment.created_at)]

        if with_type:
            values += [indent_str + 'Experiment']
        if with_params:
            values += [params(experiment)]

        rows.append(values)

    return rows

def show_experiment_group(group):
    print("ID: {}".format(group.short_id))
    print("Type: Set")
    print("State: {}".format(group.state))
    print("Project: {}".format(group.changeset.repository.name))

    if group.framework == 'tensorflow' and group.framework_config.tensorboard:
        tensorboard_job = next(job for job in group.jobs if job.role == 'tensorboard')
        print("Tensorboard: {}/{}".format(ENDPOINT_URL, tensorboard_job.service_name))

    print()
    util.print_table(
        header=['EXP ID', 'STATE', 'AGE', 'PARAMS'],
        min_widths=(6, 9, 13, 14),
        rows=get_experiments_rows(group, with_project=False, with_type=False, indent=False)
    )

    if group.jobs:
        print()
        show_job_table(group.jobs)


def show_experiments(experiments, all=False, collapsed=True, users=False):
    header = ['ID', 'PROJECT', 'STATE', 'AGE', 'TYPE']
    widths = (6, 14, 9, 13, 15)

    if not collapsed:
        header += ['PARAMS']
        widths += (14, )

    rows = []

    for experiment in experiments:
        if not all and experiment.state in ['FINISHED', 'KILLED', 'FAILED']:
            continue

        values = [
            '.{}.{}'.format(experiment.user.username, experiment.short_id) if users else experiment.short_id,
            experiment.changeset.repository.name,
            experiment.state,
            util.get_since_str(experiment.created_at),
            'Experiment' if len(experiment.children) == 0 else 'Series'
        ]

        if not collapsed:
            values += ['']

        rows.append(values)

        if not collapsed and len(experiment.children) > 0:
            rows += get_experiments_rows(experiment)

    util.print_table(
        header=header,
        min_widths=widths,
        rows=rows
    )