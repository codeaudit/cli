# -*- coding: utf-8 -*-

from __future__ import print_function

import json

from riseml.client import DefaultApi, ApiClient

from riseml import util
from riseml.errors import handle_error
from riseml.consts import API_URL, ENDPOINT_URL


def add_status_parser(subparsers):
    parser = subparsers.add_parser('status', help="show (running) experiments")
    parser.add_argument('id', help='id of specific experiment/series for which to show status', nargs='?')
    parser.add_argument('-a', '--all', help="show all experiments", action="store_const", const=True)
    parser.add_argument('-l', '--long', help="expand series", action="store_const", const=True)
    parser.set_defaults(run=run)


def run(args):
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)

    if args.id:
        experiment = util.call_api(lambda: client.get_experiment(args.id))
        if experiment.children:
            show_experiment_group(experiment)
        else:
            show_experiment(experiment)
    else:
        show_experiments(client.get_experiments(), all=args.all, collapsed=not args.long)


def params(experiment):
    return ', '.join(['{}={}'.format(p, v) for p, v in json.loads(experiment.params).items()])


def show_experiment(experiment):
    print("ID: {}".format(experiment.short_id))
    print("Type: Experiment")
    print("State: {}".format(experiment.state))
    print("Image: {}".format(experiment.image))
    print("Framework: {}".format(experiment.framework))
    print("Framework Config:")

    for attribute, value in experiment.framework_config.to_dict().iteritems():
        if value is not None:
            print("  {}: {}".format(attribute, value))

    if experiment.framework == 'tensorflow' and experiment.framework_config.tensorboard:
        tensorboard_job = next((job for job in experiment.jobs if job.role == 'tensorboard'), None)
        if tensorboard_job:
            print("Tensorboard: {}/{}".format(ENDPOINT_URL, tensorboard_job.service_name))

    print("Run Commands:")
    print(''.join(["  {}".format(command) for command in experiment.run_commands]))
    print("Concurrent Experiments: {}".format(experiment.concurrent_experiments))
    print("Params: {}\n".format(params(experiment)))

    rows = [
        (["{}.{}".format(experiment.short_id, job.name),
         job.state,
         util.get_since_str(job.started_at),
         util.get_since_str(job.finished_at),
         'N/A', 'N/A', 'N/A']) for job in experiment.jobs
    ]

    util.print_table(
        header=['JOB ID', 'STATE', 'STARTED', 'FINISHED', 'GPU', 'CPU', 'MEM'],
        min_widths=[13, 13, 13, 13, 6, 6, 6],
        rows=rows
    )


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
    print("Type: Series")
    print("State: {}".format(group.state))
    print("Project: {}".format(group.changeset.repository.name))

    if group.framework == 'tensorflow' and group.framework_config.tensorboard:
        tensorboard_job = next(job for job in group.jobs if job.role == 'tensorboard')
        print("Tensorboard: {}/{}".format(ENDPOINT_URL, tensorboard_job.service_name))

    print()

    util.print_table(
        header=['ID', 'STATE', 'AGE', 'PARAMS'],
        min_widths=(6, 9, 13, 14),
        rows=get_experiments_rows(group, with_project=False, with_type=False, indent=False)
    )


def show_experiments(experiments, all=False, collapsed=True):
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
            experiment.short_id,
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