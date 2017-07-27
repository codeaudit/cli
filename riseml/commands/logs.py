from riseml.client import DefaultApi, ApiClient


def add_logs_parser(subparsers):
    parser = subparsers.add_parser('logs', help="show logs")
    parser.add_argument('training', help="job identifier (optional)", nargs='?')
    parser.set_defaults(run=run)

def run(args):
    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)
    if args.training:
        training = client.get_training(args.training)
    else:
        project = get_project(get_project_name())
        trainings = client.get_repository_trainings(project.id)
        if not trainings:
            return
        training = trainings[0]

    stream_training_log(training)