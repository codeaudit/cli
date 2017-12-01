import sys
import json

from riseml.ansi import bold

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
    if 'feature_not_available' in msg:
        handle_feature_unavailable()
    else:
        handle_error(msg, status_code)


def handle_feature_unavailable():
    print("This feature is not available in your installation. "
          "Run " + bold('riseml account upgrade') + " to upgrade your account.")
    sys.exit(1)