import sys
import os
import subprocess
import contextlib

import yaml
import requests


class ConfigException(Exception): pass


@contextlib.contextmanager
def chdir(new_dir):
    old_dir = os.getcwd()
    try:
        os.chdir(new_dir)
        sys.path.insert(0, new_dir)
        yield
    finally:
        del sys.path[0]
        os.chdir(old_dir)


class Config(object):
    data = None
    script = None

    def download(self):
        filename = os.path.basename(self.data)
        if os.path.exists(filename):
            return

        with open(filename, 'wb') as f:
            r = requests.get(self.data, stream=True)
            if not r.ok:
                assert False
            for buf in r.iter_content(4096):
                f.write(buf)

    def run(self, work_dir='.'):
        with chdir(work_dir):
            proc = subprocess.Popen(self.script,
                shell=True,
                bufsize=1)
            proc.communicate()
            if work_dir:
                tmp_dir = os.getcwd()
                os.chdir(work_dir)


def parse(f):
    tmp = yaml.load(f)
    if not 'image' in tmp:
        raise ConfigException(u'missing key: image')
    elif not 'script' in tmp:
        raise ConfigException(u'missing key: script')

    config = Config()
    if 'data' in tmp:
        config.data = tmp['data'][0]
    config.image = tmp['image'][0]
    config.script = tmp['script'][0]
    return config

def parse_file(filename):
    with open(filename) as f:
        return parse(f)
