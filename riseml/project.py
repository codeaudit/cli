import os
import sys
import subprocess
import requests
from builtins import input

from config_parser import RepositoryConfig

from riseml.util import resolve_path
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


def get_project_root(cwd=None):
    if cwd is None:
        cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, 'riseml.yml')):
        return cwd
    elif cwd != '/':
        return get_project_root(os.path.dirname(cwd))


def get_project(name):
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)
    for project in client.get_repositories():
        if project.name == name:
            return project

    handle_error("project not found: %s" % name)


def get_project_name():
    project_root = get_project_root()
    if not project_root:
        handle_error("no riseml project found")

    config_path = os.path.join(project_root, 'riseml.yml')
    config = RepositoryConfig.from_yml_file(config_path)
    return config.project


def init_project(config_file_path, project_name):
    cwd = os.getcwd()
    if os.path.exists(os.path.join(cwd, config_file_path)):
        handle_error('%s already exists' % config_file_path)
        return

    if not project_name:
        project_name = os.path.basename(cwd)
        if not project_name:
            project_name = input('Please type project name: ')
            if not project_name:
                handle_error('Invalid project name')

    contents = project_template.format(project_name)

    with open(config_file_path, 'a') as f:
        f.write(contents)

    print('%s successfully created' % config_file_path)


def create_project():
    cwd = os.getcwd()
    if not os.path.exists(os.path.join(cwd, 'riseml.yml')):
        project_name = os.path.basename(cwd)
        with open('riseml.yml', 'a') as f:
            f.write("project: %s\n" % project_name)

    name = get_project_name()
    api_client = ApiClient(host=API_URL)
    client = DefaultApi(api_client)
    project = client.create_repository(name)[0]
    print("project created: %s (%s)" % (project.name, project.id))


def push_project(user, project_name):
    o = urlparse(GIT_URL)
    prepare_url = '%s://%s/%s/users/%s/repositories/%s/sync/prepare' % (
        o.scheme, o.netloc, o.path, user.id, project_name)
    done_url = '%s://%s/%s/users/%s/repositories/%s/sync/done' % (
        o.scheme, o.netloc, o.path, user.id, project_name)
    res = requests.post(prepare_url)
    if res.status_code == 412 and 'Repository does not exist' in res.json()['message']:
        create_project()
        res = requests.post(prepare_url)

    if res.status_code != 200:
        handle_http_error(res)

    sync_path = res.json()['path']
    o = urlparse(SYNC_URL)
    rsync_url = '%s://%s%s/%s' % (
        o.scheme, o.netloc, o.path, sync_path)

    project_root = os.path.join(get_project_root(), '')
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
        handle_http_error(res)

    revision = res.json()['sha']
    print("done")
    return revision