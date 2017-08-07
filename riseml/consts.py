import os

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

DEFAULT_CONFIG_NAME = 'riseml.yml'

ENDPOINT_URL = os.environ.get('RISEML_ENDPOINT', 'http://127.0.0.1:8080')
SYNC_URL = os.environ.get('RISEML_SYNC_ENDPOINT', 'rsync://192.168.99.100:31876/sync')
USER_URL = os.environ.get('RISEML_USER_ENDPOINT', 'https://%s.riseml.io')
API_URL = ENDPOINT_URL + '/api'
GIT_URL = ENDPOINT_URL + '/git'
STREAM_URL = "ws://%s/stream" % urlparse(ENDPOINT_URL).netloc