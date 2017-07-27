# -*- coding: utf-8 -*-

import json

from riseml.client import DefaultApi, ApiClient

from riseml import util
from riseml.errors import handle_error
from riseml.consts import API_URL


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
        training = client.get_training(ids[0])
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
    print("Run Commands:")
    print(''.join(["  {}".format(command) for command in training.run_commands]))
    print("Max Parallel Experiments: {}".format(training.max_parallel_experiments))
    print("Params: {}\n".format(params(experiment)))

    header = ['JOB', 'STATE', 'STARTED', 'FINISHED', 'GPU', 'CPU', 'MEM']
    widths = [9, 13, 13, 13, 6, 6, 6]
    print(util.format_header(header, widths=widths))
    for job in experiment.jobs:
        values = [job.name, job.state, util.get_since_str(job.started_at),
                  util.get_since_str(job.finished_at)] + ['N/A'] * 3
        print(util.format_line(values, widths=widths))


def print_experiments(training, with_project=True, with_type=True, with_params=True, indent=True, widths=None):
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
        print(util.format_line(values, widths=widths))


def show_experiment_group(training):
    print("ID: {}".format(full_id(training)))
    print("Type: Series")
    print("State: {}".format(training.state))
    print("Project: {}\n".format(training.changeset.repository.name))

    header = ['ID', 'STATE', 'AGE', 'PARAMS']
    widths = (6, 9, 13, 14)
    print(util.format_header(header, widths=widths))
    print_experiments(training, with_project=False, with_type=False, indent=False, widths=widths)


def show_trainings(trainings, all=False, collapsed=True):
    header = ['ID', 'PROJECT', 'STATE', 'AGE', 'TYPE']
    if collapsed:
        widths = (6, 14, 9, 13, 15)
    else:
        header += ['PARAMS']
        widths = (8, 14, 9, 13, 15, 14)
    print(util.format_header(header, widths=widths))

    for training in trainings:
        if not all and training.state in ['FINISHED', 'KILLED', 'FAILED']:
            continue
        values = [training.short_id, training.changeset.repository.name,
                  training.state, util.get_since_str(training.created_at),
                  'Experiment' if len(training.experiments) == 1 else 'Series']
        if not collapsed:
            values += ['']
        print(util.format_line(values, widths=widths))
        if not collapsed and len(training.experiments) > 1:
            print_experiments(training, widths=widths)