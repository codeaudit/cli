import sys


def handle_error(message, status_code=None):
    if status_code:
        print('ERROR: %s (%d)' % (message, status_code))
    else:
        print('ERROR: %s' % message)
    sys.exit(1)


def handle_http_error(res):
    handle_error(res.json()['message'], res.status_code)