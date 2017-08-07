import os
import sys
import subprocess
import requests

from riseml.util import resolve_path
from riseml.configs import create_config, get_project_name
from riseml.errors import handle_error, handle_http_error
from riseml.client import DefaultApi, ApiClient
from riseml.consts import API_URL, GIT_URL, SYNC_URL
from riseml.project_template import project_template


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
    sys.stderr.write("Pushing code...")
    sync_cmd = [resolve_path('rsync'),
                '-rlpt',
                '--exclude=.git',
                '--delete-during',
                project_root,
                rsync_url]
    if os.path.exists(exclude_file):
        sync_cmd.insert(2, '--exclude-from=%s' % exclude_file)
    proc = subprocess.Popen(sync_cmd,
                            cwd=project_root,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    for buf in proc.stdout:
        stdout.write(buf)
        stdout.flush()

    res = proc.wait()

    if res != 0:
        sys.exit(res)
    res = requests.post(done_url, params={'path': sync_path})

    if res.status_code != 200:
        handle_http_error(res.text, res.status_code)

    revision = res.json()['sha']
    print("done")
    return revision


def get_project(name):
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)
    for project in client.get_repositories():
        if project.name == name:
            return project

    handle_error("project not found: %s" % name)