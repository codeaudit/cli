import os

from config_parser import RepositoryConfig, ConfigError

from riseml.errors import handle_error


def load_config(config_file, config_section):
    if not os.path.exists(config_file):
        handle_error("%s does not exist" % config_file)

    try:
        config = RepositoryConfig.from_yml_file(config_file)
    except ConfigError as e:
        handle_error("invalid config {}\n{}".format(config_file, e.message))
        return

    try:
        return getattr(config, config_section)
    except AttributeError:
        handle_error("config doesn't contain section for %s" % config_section)


def generate_project_name():
    cwd = os.getcwd()
    project_name = os.path.basename(cwd)
    if not project_name:
        project_name = input('Please type project name: ')
        if not project_name:
            handle_error('Invalid project name')

    return project_name


def get_project_name(config_file):
    config = RepositoryConfig.from_yml_file(config_file)
    return config.project


def create_config(config_file, template, project_name=None):
    if os.path.exists(config_file):
        return False
    if project_name is None:
        project_name = generate_project_name()

    contents = template.format(project_name=project_name)
    with open(config_file, 'a') as f:
        f.write(contents)

    return True