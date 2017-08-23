from riseml.user import get_user


def add_whoami_parser(subparsers):
    parser = subparsers.add_parser('whoami', help="show currently logged in user")
    parser.set_defaults(run=run)


def run(args):
    user = get_user()
    print("you are: %s (%s)" % (user.username, user.email))