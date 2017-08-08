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
        ids = args.id.split('.')
        training = util.call_api(lambda: client.get_training(ids[0]))

        if len(training.experiments) == 1:
            show_experiment(training, training.experiments[0])
        elif len(ids) > 1:
            experiment = next((exp for exp in training.experiments if str(exp.number) == ids[1]), None)
            if experiment:
                show_experiment(training, experiment)
            else:
                handle_error('Experiment not found')
        else:
            show_experiment_group(training)
    else:
        show_trainings(client.get_trainings(), all=args.all, collapsed=not args.long)


def full_id(training, experiment=None, job=None):
    if len(training.experiments) > 1 and experiment:
        return '{}.{}'.format(training.short_id, experiment.number)
    else:
        return training.short_id


def params(experiment):
    return ', '.join(['{}={}'.format(p, v) for p, v in json.loads(experiment.params).items()])


def show_experiment(training, experiment):
    print("ID: {}".format(full_id(training, experiment)))
    print("Type: Experiment")
    print("State: {}".format(experiment.state))
    print("Image: {}".format(training.image))
    print("Framework: {}".format(training.framework))
    print("Framework Config:")

    for attribute, value in training.framework_details.to_dict().iteritems():
        if value is not None:
            print("   {}: {}".format(attribute, value))

    if training.framework == 'tensorflow' and training.framework_details.tensorboard:
        tensorboard_job = next(job for job in training.jobs if job.role == 'tensorboard')
        print("Tensorboard: {}/{}".format(ENDPOINT_URL, tensorboard_job.service_name))

    print("Run Commands:")
    print(''.join(["  {}".format(command) for command in training.run_commands]))
    print("Max Parallel Experiments: {}".format(training.max_parallel_experiments))
    print("Params: {}\n".format(params(experiment)))

    rows = [
        ([job.name,
         job.state,
         util.get_since_str(job.started_at),
         util.get_since_str(job.finished_at),
         'N/A', 'N/A', 'N/A']) for job in experiment.jobs
    ]

    util.print_table(
        header=['JOB', 'STATE', 'STARTED', 'FINISHED', 'GPU', 'CPU', 'MEM'],
        min_widths=[9, 13, 13, 13, 6, 6, 6],
        rows=rows
    )


def get_experiments_rows(training, with_project=True, with_type=True, with_params=True, indent=True):
    rows = []

    for i, experiment in enumerate(training.experiments):
        indent_str = (u'├╴' if i < len(training.experiments) - 1 else u'╰╴') if indent else ''
        values = [indent_str + full_id(training, experiment)]

        if with_project:
            values += [training.changeset.repository.name]

        values += [experiment.state, util.get_since_str(experiment.created_at)]

        if with_type:
            values += [indent_str + 'Experiment']
        if with_params:
            values += [params(experiment)]

        rows.append(values)

    return rows


def show_experiment_group(training):
    print("ID: {}".format(full_id(training)))
    print("Type: Series")
    print("State: {}".format(training.state))
    print("Project: {}".format(training.changeset.repository.name))

    if training.framework == 'tensorflow' and training.framework_details.tensorboard:
        tensorboard_job = next(job for job in training.jobs if job.role == 'tensorboard')
        print("Tensorboard: {}/{}".format(ENDPOINT_URL, tensorboard_job.service_name))

    print()

    util.print_table(
        header=['ID', 'STATE', 'AGE', 'PARAMS'],
        min_widths=(6, 9, 13, 14),
        rows=get_experiments_rows(training, with_project=False, with_type=False, indent=False)
    )


def show_trainings(trainings, all=False, collapsed=True):
    header = ['ID', 'PROJECT', 'STATE', 'AGE', 'TYPE']
    widths = (6, 14, 9, 13, 15)

    if not collapsed:
        header += ['PARAMS']
        widths += (14, )

    rows = []

    for training in trainings:
        if not all and training.state in ['FINISHED', 'KILLED', 'FAILED']:
            continue

        values = [
            training.short_id,
            training.changeset.repository.name,
            training.state,
            util.get_since_str(training.created_at),
            'Experiment' if len(training.experiments) == 1 else 'Series'
        ]

        if not collapsed:
            values += ['']

        rows.append(values)

        if not collapsed and len(training.experiments) > 1:
            rows += get_experiments_rows(training)

    util.print_table(
        header=header,
        min_widths=widths,
        rows=rows
    )