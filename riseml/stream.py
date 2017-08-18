from __future__ import print_function

import re
import json
import sys
import websocket

from riseml.errors import handle_error
from riseml.consts import STREAM_URL

from . import util

ANSI_ESCAPE_REGEX = re.compile(r'\x1b[^m]*m')


class LogPrinter(object):
    def __init__(self, ids_to_name):
        self.ids_to_name = ids_to_name

        self.job_ids_color = {
            id: list(util.COLOR_CODES.keys())[(i + 1) % len(util.COLOR_CODES)]
            for i, id in enumerate(list(self.ids_to_name.keys()))
        }

        self.job_ids_last_color_used = {}
        self.indentation = max([len(name) for _, name in self.ids_to_name.items()]) + 1

    def _message_prefix(self, msg):
        job_name = self.ids_to_name[msg['job_id']]
        color = self.job_ids_color[msg['job_id']]
        prefix = "{}| ".format(job_name.ljust(self.indentation))

        return util.color_string(prefix, color=color)

    def print_log_message(self, msg):
        if msg['job_id'] not in self.ids_to_name:
            return
        for line in msg['log_lines']:
            last_color = self.job_ids_last_color_used.get(msg['job_id'], 0)

            line_text = "[%s] %s" % (util.str_timestamp(line['time']), line['log'])

            output = "%s%s" % (self._message_prefix(msg), util.color_string(line_text, ansi_code=last_color))
            used_colors = ANSI_ESCAPE_REGEX.findall(line_text)

            if used_colors:
                self.job_ids_last_color_used[msg['job_id']] = used_colors[-1]

            print(output)

    def print_state_message(self, msg):
        if msg['job_id'] not in self.ids_to_name:
            return
        state = "[%s] --> %s" % (util.str_timestamp(msg['time']), msg['new_state'])
        output = "%s%s" % (self._message_prefix(msg),
                           util.color_string(state, color="bold_white"))
        print(output)


def stream_log(url, ids_to_name, stream_meta={}):
    log_printer = LogPrinter(ids_to_name)

    def on_message(ws, message):
        msg = json.loads(message)
        msg_type = msg['type']

        if msg_type == 'log':
            log_printer.print_log_message(msg)
        elif msg_type == 'state':
            log_printer.print_state_message(msg)

    def on_error(ws, e):
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            any_id = stream_meta.get('experiment_id') or stream_meta.get('job_id')
            print()  # newline after ^C
            if stream_meta.get('experiment_id'):
                print('Experiment will continue in background')
            else:
                print('Job will continue in background')
            if any_id:
                print('Type `riseml logs %s` to connect to log stream again' % any_id)            
        else:
            # all other Exception based stuff goes to `handle_error`
            handle_error(e)

    def on_close(ws):
        sys.exit(0)

    ws = websocket.WebSocketApp(
        url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # FIXME: {'Authorization': os.environ.get('RISEML_APIKEY')}
    ws.run_forever()


def stream_job_log(job):
    ids_to_name = { job.id: job.short_id }
    url = '%s/ws/jobs/%s/stream' % (STREAM_URL, job.id)
    stream_log(url, ids_to_name, stream_meta={ "job_id": job.short_id })


def stream_experiment_log(experiment):
    def add_experiment_to_log(experiment):
        ids_to_name[experiment.id] = experiment.short_id
        for job in experiment.jobs:
            ids_to_name[job.id] = '{}.{}'.format(experiment.short_id, job.name)
            
    url = '%s/ws/experiments/%s/stream' % (STREAM_URL, experiment.id)
    ids_to_name = {}
    add_experiment_to_log(experiment)
    for experiment in experiment.children:
        add_experiment_to_log(experiment)

    stream_log(url, ids_to_name, stream_meta={"experiment_id": experiment.short_id})
