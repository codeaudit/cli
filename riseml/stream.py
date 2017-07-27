import re
import json
import sys
import websocket

from . import util
from riseml.errors import handle_error

ANSI_ESCAPE_REGEX = re.compile(r'\x1b[^m]*m')


def stream_log(url, ids_to_name):
    def print_log_message(msg):
        for line in msg['log_lines']:
            last_color = job_ids_last_color_used.get(msg['job_id'], '')

            line_text = "[%s] %s" % (util.str_timestamp(line['time']), line['log'])

            output = "%s%s%s%s" % (message_prefix(msg), last_color, line_text, util.ansi_sequence(0))
            used_colors = ANSI_ESCAPE_REGEX.findall(line_text)
            if used_colors:
                job_ids_last_color_used[msg['job_id']] = used_colors[-1]
            print output

    def print_state_message(msg):
        state = "[%s] --> %s" % (util.str_timestamp(msg['time']), msg['new_state'])
        output = "%s%s" % (message_prefix(msg),
                           util.color_string("bold_white", state))
        print(output)

    def message_prefix(msg):
        job_name = ids_to_name[msg['job_id']]
        color = job_ids_color[msg['job_id']]
        prefix = "{}| ".format(job_name.ljust(indentation))
        return util.color_string(color, prefix)

    job_ids_color = {id: util.COLOR_CODES.keys()[(i + 1) % len(util.COLOR_CODES)]
                     for i, id in enumerate(ids_to_name.keys())}
    job_ids_last_color_used = {}
    indentation = max([len(name) for _,name in ids_to_name.items()]) + 1

    def on_message(ws, message):
        msg = json.loads(message)

        msg_type = msg['type']
        if msg_type == 'log':
            print_log_message(msg)
        elif msg_type == 'state':
            print_state_message(msg)

    def on_error(ws, error):
        handle_error(error)

    def on_close(ws):
        # print("Stream closed")
        sys.exit(0)

    ws = websocket.WebSocketApp(
        url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # FIXME: {'Authorization': os.environ.get('RISEML_APIKEY')}
    ws.run_forever()
