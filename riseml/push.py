import os
import sys
import subprocess
import requests

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from riseml.client import DefaultApi, ApiClient

try:
    stdout = sys.stdout.buffer
except AttributeError:
    stdout = sys.stdout


def create_project():
    cwd = os.getcwd()
    if not os.path.exists(os.path.join(cwd, 'riseml.yml')):
        project_name = os.path.basename(cwd)
        with open('riseml.yml', 'a') as f:
            f.write("project: %s\n" % project_name)
    name = get_project_name()
    api_client = ApiClient(host=api_url)
    client = DefaultApi(api_client)
    project = client.create_repository(name)[0]
    print("project created: %s (%s)" % (project.name, project.id))


def push_project(user, project_name):
    o = urlparse(git_url)
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
    o = urlparse(sync_url)
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