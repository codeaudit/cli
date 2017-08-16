from __future__ import print_function

import re
import json
import sys
import time
import websocket
import threading
import StringIO
import math
import os
from collections import OrderedDict

from riseml.errors import handle_error
from riseml.consts import STREAM_URL

from . import util
from riseml.util import bytes_to_gib


def formatted_output(getter):
    def format_output(self, format=None, transform=None):
        v = getter(self)
        if transform and v is not None:
            v = transform(v)
        if format:
            if v is not None:
                return format % v
            else:
                return 'N/A'
        return v
    return format_output


def stream_stats(job_id_stats, stream_meta={}):
    job_ids = job_id_stats.keys()
    url = '%s/ws/monitor/?jobId=%s' % (STREAM_URL, job_ids[0])
    if len(job_ids) > 1:
        url += '&' + '&'.join(['jobId=%s' % job_id for job_id in job_ids[1:]])

    def on_message(ws, message):
        msg = json.loads(message)
        job_id = msg['job_id']
        job_stats = job_id_stats[job_id]
        job_stats.update(msg)

    def on_error(ws, e):
        if isinstance(e, (KeyboardInterrupt, SystemExit)):
            if stream_meta.get('training_id'):
                print()
                print('Experiment will continue in background')
                print('Type `riseml logs %s` to connect to log stream again' % stream_meta['training_id'])
            else:
                print()  # newline after ^C
                print('Job will continue in background')

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
    wst = threading.Thread(target=ws.run_forever)
    wst.daemon = True
    wst.start()
    conn_timeout = 10
    while not ws.sock.connected and conn_timeout > 0:
        time.sleep(0.5)
        conn_timeout -= 1
    if not ws.sock.connected:
        handle_error('Unable to connect to monitor stream')


class GPUStats():

    def __init__(self, device_name):
        self.device_name = device_name
        self.stats = {}
        self.timestamp = 0

    def update(self, stats, timestamp=None):
        if not timestamp:
            timestamp = stats.pop('timestamp')
        self.timestamp = timestamp
        self.stats.update(stats)

    @formatted_output
    def get_mem_usage(self):
        return self.stats.get('mem_used')

    @formatted_output
    def get_mem_total(self):
        return self.stats.get('mem_total')

    @formatted_output
    def get_util(self):
        return self.stats.get('gpu_utilization')


class JobStats():

    def __init__(self, job):
        self.job = job
        self.stats = {}
        self.timestamp = 0
        # dict from name -> GPUStats
        self.gpu_stats = {}
        # sorted names of all gpus
        self.gpus = []
            
    def update(self, stats, timestamp=None):
        if not timestamp:
            timestamp = stats.pop('timestamp')
        if 'gpus' in stats:
            gpu_stats = stats.pop('gpus')
            self._update_gpu_stats(gpu_stats, timestamp)
        self._update_stats(stats, timestamp)
    
    def _update_stats(self, stats, timestamp):
        self.timestamp = timestamp
        self.stats.update(stats)
    
    def _update_gpu_stats(self, gpu_stats, timestamp):
        for gpu, stats in gpu_stats.items():
            s = self.gpu_stats.get(gpu, GPUStats(gpu))
            s.update(stats, timestamp=timestamp)
            self.gpu_stats[gpu] = s
        self.gpus = sorted(list(set(self.gpus) + set(gpu_stats.keys())))
    
    @formatted_output
    def get_cpu_percent(self):
        return self.stats.get('cpu_percent')
    
    @formatted_output
    def get_mem_total(self):
        return self.stats.get('memory_limit')

    @formatted_output
    def get_mem_usage(self):
        return self.stats.get('memory_usage')

    @formatted_output
    def get_mem_percent(self):
        usage = self.get_mem_usage()
        total = self.get_mem_total()
        if usage is not None and total is not None and total > 0:
            return (float(usage) / float(total)) * 100

    @formatted_output
    def get_gpu_mem_usage(self):
        if self.gpus:
            return sum([g.get_mem_usage() for g in self.gpu_stats.values()])

    @formatted_output
    def get_gpu_percent(self):
        if self.gpus:
            return sum([s.get_util() for s in self.gpu_stats.values()])

    @formatted_output
    def get_gpu_mem_total(self):
        if self.gpus:
            return sum([g.get_mem_total() for g in self.gpu_stats.values()])
    
    @formatted_output
    def get_gpu_mem_percent(self):
        usage = self.get_gpu_mem_usage()
        total = self.get_gpu_mem_total()
        if usage is not None and total is not None and total > 0:
            return (float(usage) / float(total)) * 100


def get_summary_table(job_id_stats):
    rows = []
    output = StringIO.StringIO()
    for job_id, job_stats in job_id_stats.items():
        job = job_stats.job
        if job.state in ('RUNNING'):
            rows.append([job.short_id, job.changeset.repository.name, job.state,
                         job_stats.get_cpu_percent('%d'), job_stats.get_mem_percent('%d'), 
                         '%s / %s' % (job_stats.get_mem_usage('%.1f', transform=bytes_to_gib), 
                                      job_stats.get_mem_total('%.1f', transform=bytes_to_gib)),
                         job_stats.get_gpu_percent('%d'), job_stats.get_gpu_mem_percent('%d'),
                         '%s / %s' % (job_stats.get_gpu_mem_usage('%.1f', transform=bytes_to_gib), 
                                      job_stats.get_gpu_mem_total('%.1f', transform=bytes_to_gib))])
        else:
            rows.append([job.short_id, job.changeset.repository.name, job.state] + ['N/A' for _ in range(6)])

    util.print_table(
        header=['ID', 'PROJECT', 'STATE', 
                'CPU %', 'MEM %', 'MEM USAGE / TOTAL', 
                'GPU %', 'GPU-MEM %', 'GPU-MEM USAGE / TOTAL'],
        min_widths=[4, 6, 9, 6, 6, 12, 6, 6, 12],
        rows=rows,
        file=output
    )
    return output.getvalue()


class StatsScreen():

    def __init__(self, job_id_stats):
        self.job_id_stats = job_id_stats

    def _display(self, stdscr):
        while True:
            sys.stdout.flush()
            os.system('cls' if os.name == 'nt' else 'clear')
            summary_table = get_summary_table(self.job_id_stats)            
            print(summary_table)
            time.sleep(1)      

    def display(self):
        self._display(None)


def stream_monitor(training, experiment_id):
    jobs = []
    if experiment_id:
        experiment = next((exp for exp in training.experiments if exp.number == int(experiment_id)), None)
        if not experiment:
            handle_error("Could not find experiment")
    else:
        jobs = training.jobs
    jobs = sorted(jobs, key=lambda j: j.short_id)
    job_id_stats = OrderedDict({j.id: JobStats(j) for j in jobs if j.role == 'train'})
    screen = StatsScreen(job_id_stats)
    stream_stats(job_id_stats)
    screen.display()


# detail
#  4.2.worker0 - (state: ..., node: ...., pod: ....)
#    Memory Stats
#    Total MB  XX Used MB XX
#    -------------------------------------------------------------
#    CPU Utilisation
#    -------------------------------------------------------------
#    CPU       | 0        |25         |50          |75        100|
#    1    XX%  | xxxxxxxx>
#    2    XX%  | xxxxxxxxxxxx>
#    3    XX%  | xxxx>
#    4    XX%  | xxxxxx>
#    GPU Utilisation
#    ----------------------------------------------------------------------------
#    GPU      Name       GPU-Util  Mem-Used  Mem-Total  Pwr-Used  Pwr-Limit  Temp
#    nvidia0  Tesla K80  42%
#    nvidia1
#    nvidia2
