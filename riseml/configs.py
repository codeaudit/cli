import os
import yaml

from riseml.errors import handle_error


def load_config(config_file, config_section):
    if not os.path.exists(config_file):
        handle_error("%s does not exist" % config_file)

    with open(config_file, 'r') as f:
        config = yaml.load(f.read())

        if config_section not in config:
            handle_error("config doesn't contain section for %s" % config_section)

        return config[config_section]