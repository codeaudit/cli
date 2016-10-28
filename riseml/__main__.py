import os
import sys

from riseml.config_parser import parse_file


path = sys.argv[1]
config = parse_file(os.path.join(path, 'riseml.yml'))
config.download()
config.run(path)
