import sys
import json

def handle_error(message, status_code=None, exit_code=1):
    if status_code:
        print('ERROR: %s (%d)' % (message, status_code))
    else:
        print('ERROR: %s' % message)
    sys.exit(exit_code)


def handle_http_error(text, status_code):
    try:
        msg = json.loads(text)['message']
    except (ValueError, KeyError):
        msg = text

    handle_error(msg, status_code)