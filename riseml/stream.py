from __future__ import print_function

import re
import json
import sys
import websocket
import stringcase

from riseml.errors import handle_error
from riseml.consts import STREAM_URL

from . import util

ANSI_ESCAPE_REGEX = re.compile(r'\x1b\[(\d+)m')
TENSORBOARD_STARTING_REGEX = re.compile(r'Starting TensorBoard (\d+) at (http://[^:]+:\d+)')

class LogPrinter(object):
    def __init__(self, url, ids_to_name, stream_meta=None):
        self.url = url
        self.ids_to_name = ids_to_name
        self.stream_meta = stream_meta or {}

        self.job_ids_color = {
            id: list(util.COLOR_CODES.keys())[(i + 1) % len(util.COLOR_CODES)]
            for i, id in enumerate(list(self.ids_to_name.keys()))
        }

        self.job_ids_last_color_used = {}
        self.indentation = max([len(name) for _, name in self.ids_to_name.items()]) + 1

    def stream(self):
        ws_app = websocket.WebSocketApp(
            self.url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        # FIXME: {'Authorization': os.environ.get('RISEML_APIKEY')}
        ws_app.run_forever()

    def _on_message(self, _, message):
        msg = json.loads(message)
        msg_type = msg['type']

        if msg_type == 'log':
            self.print_log_message(msg)
        elif msg_type == 'state':
            self.print_state_message(msg)

    def _on_error(self, _, error):
        if isinstance(error, (KeyboardInterrupt, SystemExit)):
            any_id = self.stream_meta.get('experiment_id') or self.stream_meta.get('job_id')
            print()  # newline after ^C
            if self.stream_meta.get('experiment_id'):
                print('Experiment will continue in background')
            else:
                print('Job will continue in background')
            if any_id:
                print('Type `riseml logs %s` to connect to log stream again' % any_id)
        else:
            # all other Exception based stuff goes to `handle_error`
            handle_error(error)

    def _on_close(self, _):
        sys.exit(0)

    def _message_prefix(self, msg):
        job_name = self.ids_to_name[msg['job_id']]
        color = self.job_ids_color[msg['job_id']]
        prefix = "{}| ".format(job_name.ljust(self.indentation))

        return util.color_string(prefix, color=color)

    def print_log_message(self, msg):
        if msg['job_id'] not in self.ids_to_name:
            return
        line = msg['line']
        if 'tensorboard' in self.ids_to_name[msg['job_id']] \
            and self.stream_meta.get("tensorboard_job"):
            line = re.sub(TENSORBOARD_STARTING_REGEX,
                            r'Starting Tensorboard \1 at {}'.format(
                                util.tensorboard_job_url(self.stream_meta.get("tensorboard_job"))
                            ),
                            line)
        for partial_line in line.split('\r'):
            last_color = self.job_ids_last_color_used.get(msg['job_id'], 0)
            line_text = "[%s] %s" % (util.str_timestamp(msg['time']),
                                    util.color_string(partial_line, ansi_code=last_color))

            output = "%s%s" % (self._message_prefix(msg), line_text)
            sys.stdout.write(output)
            sys.stdout.write('\r')

            used_colors = ANSI_ESCAPE_REGEX.findall(partial_line)
            if used_colors:
                self.job_ids_last_color_used[msg['job_id']] = used_colors[-1]
        sys.stdout.write('\n')

    def print_state_message(self, msg):
        if msg['job_id'] not in self.ids_to_name:
            return
        time = util.str_timestamp(msg['time'])
        state = "[%s] --> %s" % (time, msg['state'])
        output = "%s%s" % (self._message_prefix(msg),
                           util.color_string(state, color="bold_white"))
        print(output)
        for key in ['reason', 'message', 'exit_code']:
            if msg.get(key, None) is not None:
                message = "[{}] {}: {}".format(time, stringcase.titlecase(key), msg[key])
                print("{}{}".format(self._message_prefix(msg), util.color_string(message, color="bold_white")))


def stream_job_log(job):
    ids_to_name = {job.id: job.short_id}
    url = '%s/ws/jobs/%s/stream' % (STREAM_URL, job.id)
    meta = {"job_id": job.short_id}
    if util.is_tensorboard_job(job):
        meta["tensorboard_job"] = job
    LogPrinter(url, ids_to_name, stream_meta=meta).stream()


def stream_experiment_log(experiment):
    def add_experiment_to_log(experiment):
        ids_to_name[experiment.id] = experiment.short_id
        for job in experiment.jobs:
            ids_to_name[job.id] = '{}.{}'.format(experiment.short_id, job.name)

    url = '%s/ws/experiments/%s/stream' % (STREAM_URL, experiment.id)
    ids_to_name = {}
    add_experiment_to_log(experiment)
    for child_experiment in experiment.children:
        add_experiment_to_log(child_experiment)

    meta = {"experiment_id": experiment.short_id}
    if util.has_tensorboard(experiment):
        meta["tensorboard_job"] = util.tensorboard_job(experiment)
    LogPrinter(url, ids_to_name, stream_meta=meta).stream()
