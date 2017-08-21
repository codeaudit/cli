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
from riseml.util import bytes_to_gib, print_table, bold

stats_lock = threading.Lock()

def formatted_getter(getter):
    def format_output(self, fmt=None, trans=None):
        v = getter(self)
        if trans and v is not None:
            v = trans(v)
        if fmt:
            if v is not None:
                return fmt % v
            else:
                return 'N/A'
        return v
    return format_output


class Stats():
    
    def get(self, stat_name, fmt=None, transform=None):
        @formatted_getter
        def get(self):
            if hasattr(self, 'get_%s' % stat_name):
                return getattr(self, 'get_%s' % stat_name)()
            else:
                return self.stats.get(stat_name)
        return get(self, fmt, transform)


class GPUStats(Stats):

    def __init__(self, device_name):
        self.device_name = device_name
        self.stats = {}
        self.timestamp = 0

    def update(self, stats, timestamp=None):
        if not timestamp:
            timestamp = stats.pop('timestamp')
        self.timestamp = timestamp
        self.stats.update(stats)


class JobStats(Stats):

    def __init__(self, job):
        self.job = job
        self.stats = {}
        self.timestamp = 0
        # dict from device name -> GPUStats
        self.gpu_stats = {}
        # sorted device names of all gpus
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
        self.gpus = sorted(list(set(self.gpus) | set(gpu_stats.keys())))

    @formatted_getter
    def get_memory_percent(self):
        usage = self.get('memory_used')
        total = self.get('memory_total')
        if usage is not None and total is not None and total > 0:
            return (float(usage) / float(total)) * 100

    @formatted_getter
    def get_gpu_memory_used(self):
        if self.gpus:
            return sum([g.get('memory_used') for g in self.gpu_stats.values()])

    @formatted_getter
    def get_gpu_percent(self):
        if self.gpus:
            return sum([s.get('gpu_utilization') for s in self.gpu_stats.values()])

    @formatted_getter
    def get_gpu_memory_total(self):
        if self.gpus:
            return sum([g.get('memory_total') for g in self.gpu_stats.values()])
    
    @formatted_getter
    def get_gpu_memory_percent(self):
        usage = self.get('gpu_memory_used')
        total = self.get('gpu_memory_total')
        if usage is not None and total is not None and total > 0:
            return (float(usage) / float(total)) * 100


def get_summary_infos(job_id_stats):
    rows = []
    output = StringIO.StringIO()
    for job_id, job_stats in job_id_stats.items():
        job = job_stats.job
        if job.state in ('RUNNING'):
            print(job_stats.get('memory_used'), job_stats.get('memory_limit'))
            mem_used = job_stats.get('memory_used', '%.1f', bytes_to_gib)
            mem_total = job_stats.get('memory_limit', '%.1f', bytes_to_gib)
            gpu_mem_used = job_stats.get('gpu_memory_used', '%.1f', bytes_to_gib)
            gpu_mem_total = job_stats.get('gpu_memory_total', '%.1f', bytes_to_gib)
            rows.append([job.short_id, job.changeset.repository.name, job.state,
                         job_stats.get('cpu_percent', '%d'), 
                         job_stats.get('memory_percent', '%d'), 
                         '%s / %s' % (mem_used, mem_total),
                         job_stats.get('gpu_percent', '%d'), 
                         job_stats.get('gpu_memory_percent', '%d'),
                         '%s / %s' % (gpu_mem_used, gpu_mem_total)])
        else:
            rows.append([job.short_id, job.changeset.repository.name, job.state] + ['N/A' for _ in range(6)])

    print_table(
        header=['ID', 'PROJECT', 'STATE', 
                'CPU %', 'MEM %', 'MEM-Used / Total', 
                'GPU %', 'GPU-MEM %', 'GPU-MEM Used / Total'],
        min_widths=[4, 6, 9, 6, 6, 12, 6, 6, 12],
        rows=rows,
        file=output
    )
    return output.getvalue()
        

def get_cpu_bars(num_cpus, percpu_percent):
    cpu_col_width = 10
    bar_width = 62
    bar_header = '0%s100|' % (' ' * (bar_width - 4))
    total_width = cpu_col_width + 2 + len(bar_header)
    separator = '-' * total_width
    for i in (25.0, 50.0, 75.0):
        offset = int(round(i / 100 * bar_width)) - 1
        tick = '|%d' % int(i)
        bar_header = bar_header[0:offset] + tick + bar_header[offset + len(tick):]
    bar_lines = []
    def get_bar_line(cpu_index, percent):
        percent = min(percent, 100.0)
        length = int(round(round(percent) / 100 * bar_width))
        bar = '=' * (length - 1) 
        if percent > 0:
            bar += '>'
        fill = ' ' * (bar_width - len(bar)) + '|'
        line = '{:<3}{:>{right}.1f}% |{}'.format(cpu_index, percent, 
                                                 bar + fill, 
                                                 right=cpu_col_width - 4)
        return line
    if percpu_percent:
        for i, p in enumerate(percpu_percent):
            bar_lines.append(get_bar_line(i, p))
    for _ in range(num_cpus - len(bar_lines)):
        bar_lines.append(get_bar_line('N/A', 0))
    header = '{:<{w}} |{}'.format('CPU Stats', bar_header,
                                  w=cpu_col_width)
    return '\n'.join([separator, header] + bar_lines)


def get_gpu_table(job_stats):
    rows = []
    output = StringIO.StringIO()
    for gpu_dev in job_stats.gpus:
        gpu_stats = job_stats.gpu_stats[gpu_dev]
        row = [gpu_dev, gpu_stats.get('name', '%s'), 
               gpu_stats.get('gpu_utilization', '%d'),
               gpu_stats.get('memory_used', '%.1f', bytes_to_gib),
               gpu_stats.get('memory_total', '%.1f', bytes_to_gib),
               gpu_stats.get('power_draw', '%d'),
               gpu_stats.get('power_limit', '%d'),
               gpu_stats.get('temperature', '%d')]
        rows.append(row)
    for _ in range(job_stats.job.gpus - len(job_stats.gpus)):
        row = ['N/A'] + ['' for _ in range(7)]
        rows.append(row)
    if rows:
        print_table(
            header=['GPU Stats', 'NAME', 'GPU-Util', 
                    'MEM-Used', 'MEM-Total', 
                    'PWR-Used', 'PWR-Limit', 'TEMP'],
            min_widths=[4, 8, 3, 4, 4, 3, 3, 3],
            rows=rows,
            separator=True,
            bold_header=False,
            file=output
        )
    return output.getvalue().strip()


def indent(text, spaces=2):
    lines = text.split('\n')
    return '\n'.join(['%s%s' % (' ' * spaces, l) for l in lines])


def get_detailed_info(job_stats):
    output = StringIO.StringIO()
    job = job_stats.job    
    caption = bold('%s (STATE: %s)' % (job.short_id, job.state))
    if job.state in ('RUNNING'):
        total_gib = job_stats.get('memory_limit', '%.1f', bytes_to_gib)
        used_gib = job_stats.get('memory_used', '%.1f', bytes_to_gib)
        memory = 'Memory Stats (Used/Total) GiB: %s / %s' % (used_gib, total_gib)
        cpu_bars = get_cpu_bars(job.cpus, 
                                job_stats.get('percpu_percent'))
        gpu_table = get_gpu_table(job_stats)
        return '\n'.join([caption, indent(memory), 
                          indent(cpu_bars), indent(gpu_table)])
    else:
        return '\n'.join([caption, indent('No real-time stats available')])
                

def get_detailed_infos(job_id_stats):
    output = StringIO.StringIO()
    for job_id, stats in job_id_stats.items():
        output.write(get_detailed_info(stats))
        output.write('\n\n')
    return output.getvalue()


class StatsScreen():

    def __init__(self, job_id_stats):
        self.job_id_stats = job_id_stats

    def _display(self, detailed):
        while True:
            sys.stdout.flush()
            os.system('cls' if os.name == 'nt' else 'clear')
            with stats_lock:
                if detailed:
                    stats_screen = get_detailed_infos(self.job_id_stats)
                else:
                    stats_screen = get_summary_infos(self.job_id_stats)            
            print(stats_screen.strip())
            sys.stdout.flush()
            time.sleep(1)      

    def display(self, detailed=False):
        self._display(detailed)


def stream_stats(job_id_stats, stream_meta={}):
    job_ids = job_id_stats.keys()
    url = '%s/ws/monitor/?jobId=%s' % (STREAM_URL, job_ids[0])
    if len(job_ids) > 1:
        url += '&' + '&'.join(['jobId=%s' % job_id for job_id in job_ids[1:]])

    def on_message(ws, message):
        msg = json.loads(message)
        job_id = msg['job_id']
        with stats_lock:
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


def monitor_jobs(jobs, detailed=False):
    jobs = sorted(jobs, key=lambda j: j.short_id)
    job_id_stats = OrderedDict({j.id: JobStats(j) for j in jobs if j.role == 'train'})
    screen = StatsScreen(job_id_stats)
    stream_stats(job_id_stats)
    screen.display(detailed=detailed)


if __name__ == '__main__':
    from collections import namedtuple
    Job = namedtuple('Job', ['short_id', 'id', 'state', 'changeset', 'gpus', 'cpus'])
    Changeset = namedtuple('Changeset', ['repository'])
    Repo = namedtuple('Repo', ['name'])
    
    job = Job('1.2.worker0', '123', 'RUNNING', Changeset(Repo('test')), 4, 7)
    job_2 = Job('1.2.worker1', '123', 'FINISHED', Changeset(Repo('test')), 4, 7)

    update = {'job_id': '123',
               'memory_limit': 1000000,
               'memory_used': 100000,
               'timestamp': 123123123,
               'percpu_percent': [74.4, 74.9, 75.1, 120.0]}
    g_update = {'job_id': '123',
               'timestamp': 123123123,
               'gpus': {'/dev/nvidia0': {  
                            'temperature': 73,
                            'gpu_utilization': 44,
                            'memory_free': 1000000,
                            'name': 'Tesla K80',
                            'power_draw': 240,
                            'power_limit': 250,
                            'memory_total': 12000000000,
                            'memory_used': 1000000000,
                            'memory_utilization': 42,
                            'fan_speed': 25000,
                            'host_device': '/dev/nvidia3'}
                        }}

    stats = JobStats(job)
    stats.update(update)
    stats.update(g_update)
    stats_2 = JobStats(job_2)
    job_id_stats = {job.id: stats, '234': stats, '345': stats_2}
    screen = StatsScreen(job_id_stats)
    screen.display(detailed=True)
