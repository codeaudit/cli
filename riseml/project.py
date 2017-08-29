from __future__ import print_function

import os
import sys
import re
import subprocess
import requests

from riseml.util import get_rsync_path, get_readable_size
from riseml.configs import create_config, get_project_name
from riseml.errors import handle_error, handle_http_error
from riseml.client import DefaultApi, ApiClient
from riseml.consts import API_URL, GIT_URL, SYNC_URL
from riseml.project_template import project_template
from riseml.util import bytes_to_mib

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

try:
    stdout = sys.stdout.buffer
except AttributeError:
    stdout = sys.stdout


def create_project(config_file):
    # create, if not exists
    create_config(config_file, project_template)

    name = get_project_name(config_file)
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)
    project = client.create_repository(name)[0]
    print("project created: %s (%s)" % (project.name, project.id))


def push_project(user, project_name, config_file):
    o = urlparse(GIT_URL)
    prepare_url = '%s://%s/%s/users/%s/repositories/%s/sync/prepare' % (
        o.scheme, o.netloc, o.path, user.id, project_name)
    done_url = '%s://%s/%s/users/%s/repositories/%s/sync/done' % (
        o.scheme, o.netloc, o.path, user.id, project_name)

    res = requests.post(prepare_url)
    if res.status_code == 412 and 'Repository does not exist' in res.json()['message']:
        create_project(config_file)
        res = requests.post(prepare_url)

    if res.status_code != 200:
        handle_http_error(res.text, res.status_code)

    sync_path = res.json()['path']
    o = urlparse(SYNC_URL)
    rsync_url = '%s://%s%s/%s' % (
        o.scheme, o.netloc, o.path, sync_path)

    project_root = os.path.join(os.getcwd(), '')
    exclude_file = os.path.join(project_root, '.risemlignore')
    
    sync_cmd = [get_rsync_path(),
                '-rlpt',
                '--exclude=.git',
                '--exclude=riseml*.yml',
                '--delete-during',
                project_root,
                rsync_url]
    if os.path.exists(exclude_file):
        sync_cmd.insert(2, '--exclude-from=%s' % exclude_file)
    project_size = get_project_size(sync_cmd, project_root)
    if project_size is not None:
        num_files, size = project_size
        sys.stdout.write('Syncing project (%s)...' %
                            (get_readable_size(size)))
    else:
        sys.stdout.write('Syncing project...')
    sys.stdout.flush()
    proc = subprocess.Popen(sync_cmd,
                            cwd=project_root,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    for buf in proc.stdout:
        stdout.write(buf)
        stdout.flush()

    res = proc.wait()

    if res != 0:
        handle_error('Push code failed, rsync error', exit_code=res)

    res = requests.post(done_url, params={'path': sync_path})

    if res.status_code != 200:
        handle_http_error(res.text, res.status_code)

    revision = res.json()['sha']
    sys.stdout.write('done\n')
    return revision


def get_project_size(sync_cmd, project_root):
    sync_cmd = sync_cmd[:]
    sync_cmd.insert(1, '--dry-run')
    sync_cmd.insert(1, '-v')
    try:
        out = subprocess.check_output(sync_cmd)
        m = re.search(r'total size is ([0-9,]+)  speedup', out)
        if m:
            num_files = len(out.strip().split('\n')) - 5 # 1 header, 3 footer, ./
            size = int(m.group(1).replace(',', ''))
            return num_files, size
    except subprocess.CalledProcessError:
        return None


def get_project(name):
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)
    for project in client.get_repositories():
        if project.name == name:
            return project

    handle_error("project not found: %s" % name)
