import os
import sys
from riseml.client.configuration import Configuration


DEFAULT_CONFIG_NAME = 'riseml.yml'
IS_BUNDLE = getattr(sys, 'frozen', False)
VERSION = Configuration().packageVersion