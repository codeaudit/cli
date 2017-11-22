from pathlib import Path
import os
import yaml
import sys
import errno
from .errors import handle_error

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse


CONFIG_PATH = '.riseml'
CONFIG_FILE = 'config'

EMPTY_CONFIG = """
current-context: default

contexts:
  - name: default
    context:
      cluster: default
      user: default

clusters:
  - name: default
    cluster:
      api-server: ""
      sync-server: ""
      cluster-id: ""
      environment: development

users:
- name: default
  user:
    api-key: ""
"""

def get_config_file():
    home = str(Path.home())
    return os.path.join(home, CONFIG_PATH, CONFIG_FILE)


def read_config():
    try:
        with open(get_config_file(), 'rt') as f:
            try:
                config = yaml.safe_load(f.read())
            except yaml.scanner.ScannerError as yml_error:
                handle_error('client configuration has invalid syntax: %s' % yml_error)
            return config
    except FileNotFoundError as e:
        return yaml.safe_load(EMPTY_CONFIG)


def get_cluster_config(cluster, config):
    for c in config['clusters']:
        if c['name'] == cluster:
            return c['cluster']


def get_user_config(user, config):
    for c in config['users']:
        if c['name'] == user:
            return c['user']


def get_context_config(context, config):
    for c in config['contexts']:
        if c['name'] == context:
            return c['context']


def get_current_context(config):
    if 'current-context' in config:
        current_context = config['current-context']
        if not current_context:
            handle_error('current context not available in client configuration')
        context = get_context_config(current_context, config)
        if not context:
            handle_error('context %s not available in client configuration' % current_context)
        user = get_user_config(context['user'], config)
        if not user:
            handle_error('user %s not available in client configuration' % context['user'])
        validate_user_config(user)
        cluster = get_cluster_config(context['cluster'], config)
        if not cluster:
            handle_error('cluster %s not available in client configuration' % context['cluster'])
        validate_cluster_config(cluster)
        return user, cluster
    else:
        handle_error('current context not available in client configuration')


def assert_exists(key, config):
    if not key in config or config[key] is None:
        handle_error('config key %s not present in client configuration:\n %s' % (key, config))


def validate_user_config(user_config):
    assert_exists('api-key', user_config)


def validate_cluster_config(cluster_config):
    assert_exists('api-server', cluster_config)
    assert_exists('sync-server', cluster_config)
    assert_exists('cluster-id', cluster_config)


def get_client_config():
    config = read_config()
    user, cluster = get_current_context(config)
    return { 'user': user,
             'cluster': cluster}


def generate_config(api_key, api_host, rsync_host, cluster_id, environment):
    config = """
current-context: default

contexts:
  - name: default
    context:
      cluster: default
      user: default

clusters:
  - name: default
    cluster:
      api-server: http://{api_host}
      sync-server: rsync://{rsync_host}/sync
      cluster-id: {cluster_id}
      environment: {environment}

users:
- name: default
  user:
    api-key: {api_key}
""".format(api_host=api_host,
           api_key=api_key,
           rsync_host=rsync_host,
           cluster_id=cluster_id,
           environment=environment)
    return config


def write_config(api_key, api_host, rsync_host, cluster_id,
                 environment='production'):
    try:
        os.makedirs(os.path.dirname(get_config_file()))
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
    config = generate_config(api_key, api_host, rsync_host,
                             cluster_id, environment)
    with open(get_config_file(), 'wt') as f:
        f.write(config)


def get_api_server():
    return get_client_config()['cluster']['api-server']


def get_sync_url():
    return get_client_config()['cluster']['sync-server']


def get_api_url(api_server=None):
    if not api_server:
        return get_client_config()['cluster']['api-server'] + '/api'
    else:
        return api_server + '/api'


def get_git_url():
    return get_client_config()['cluster']['api-server'] + '/git'


def get_api_key():
    return get_client_config()['user']['api-key']


def get_stream_url():
    api_server = get_client_config()['cluster']['api-server']
    return "ws://%s/stream" % urlparse(api_server).netloc


def get_rollbar_endpoint():
    default = 'https://backend.riseml.com/errors/client/'
    if get_environment() == 'staging':
        default = 'https://backend.riseml-staging.com/errors/client/'
    return get_client_config()['cluster'].get('rollbar-server', default)


def get_riseml_backend_url():
    default = 'https://riseml.com/backend/'
    if get_environment() == 'staging':
        default = 'https://riseml-staging.com/backend/'
    return get_client_config()['cluster'].get('backend', default)


def get_cluster_id():
    return get_client_config()['cluster']['cluster-id']


def get_environment():
    return get_client_config()['cluster']['environment']