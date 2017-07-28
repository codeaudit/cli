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
            id: util.COLOR_CODES.keys()[(i + 1) % len(util.COLOR_CODES)]
            for i, id in enumerate(self.ids_to_name.keys())
        }

        self.job_ids_last_color_used = {}
        self.indentation = max([len(name) for _, name in self.ids_to_name.items()]) + 1

    def _message_prefix(self, msg):
        job_name = self.ids_to_name[msg['job_id']]
        color = self.job_ids_color[msg['job_id']]
        prefix = "{}| ".format(job_name.ljust(self.indentation))

        return util.color_string(color, prefix)

    def print_log_message(self, msg):
        for line in msg['log_lines']:
            last_color = self.job_ids_last_color_used.get(msg['job_id'], '')

            line_text = "[%s] %s" % (util.str_timestamp(line['time']), line['log'])

            output = "%s%s%s%s" % (self._message_prefix(msg), last_color, line_text, util.ansi_sequence(0))
            used_colors = ANSI_ESCAPE_REGEX.findall(line_text)

            if used_colors:
                self.job_ids_last_color_used[msg['job_id']] = used_colors[-1]

            print(output)

    def print_state_message(self, msg):
        state = "[%s] --> %s" % (util.str_timestamp(msg['time']), msg['new_state'])
        output = "%s%s" % (self._message_prefix(msg),
                           util.color_string("bold_white", state))
        print(output)


def stream_log(url, ids_to_name):
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
            print('Exiting...')
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
    def flatten_jobs(job):
        for c in job.children:
            for j in flatten_jobs(c):
                yield j
        yield job

    jobs = list(flatten_jobs(job))
    ids_to_name = {job.id: util.get_job_name(job) for job in jobs}
    url = '%s/ws/jobs/%s/stream' % (STREAM_URL, job.id)
    stream_log(url, ids_to_name)


def stream_training_log(training):
    url = '%s/ws/trainings/%s/stream' % (STREAM_URL, training.id)
    ids_to_name = {}
    ids_to_name[training.id] = '{}'.format(training.short_id)
    if len(training.experiments) == 1:
        for job in training.experiments[0].jobs:
            ids_to_name[job.id] = '{}: {}'.format(training.short_id, job.name)
    else:
        for experiment in training.experiments:
            ids_to_name[experiment.id] = '{}.{}'.format(training.short_id, experiment.number)
            for job in experiment.jobs:
                ids_to_name[job.id] = '{}.{}: {}'.format(training.short_id, experiment.number, job.name)

    for job in training.jobs:
        if job.id not in ids_to_name:
            ids_to_name[job.id] = '{}: {}'.format(training.short_id, job.name)

    stream_log(url, ids_to_name)
