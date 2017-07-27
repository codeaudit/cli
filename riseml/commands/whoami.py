def add_whoami_parser(subparsers):
    parser = subparsers.add_parser('whoami', help="show currently logged in user")
    parser.set_defaults(run=run)

def run(args):
    user = get_user()
    print("%s (%s)" % (user.username, user.id))