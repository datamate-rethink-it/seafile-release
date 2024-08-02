#!/usr/bin/env python3

import configparser
import logging
import os
import sys

logger = logging.getLogger('generate-config-files')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

CONFIG_DIR = '/shared/seafile/conf'
CCNET_CONF_PATH = os.path.join(CONFIG_DIR, 'ccnet.conf')
SEAFDAV_CONF_PATH = os.path.join(CONFIG_DIR, 'seafdav.conf')
SEAFEVENTS_CONF_PATH = os.path.join(CONFIG_DIR, 'seafevents.conf')
SEAFILE_CONF_PATH = os.path.join(CONFIG_DIR, 'seafile.conf')
GUNICORN_CONF_PATH = os.path.join(CONFIG_DIR, 'gunicorn.conf.py')

# Specify default values
# Note: configparser only allows strings as values
DEFAULT_VALUES = {
    # TODO: Check if casing matters here (section names/key names)
    # TODO: Related: https://stackoverflow.com/questions/19359556/configparser-reads-capital-keys-and-make-them-lower-case
    'CCNET__Database__ENGINE': 'mysql',
    # No default value for CCNET__Database__HOST
    'CCNET__Database__PORT': '3306',
    # TODO: Use root or create database user before running this script?
    'CCNET__Database__USER': 'root',
    # No default value for CCNET__Database__PASSWD
    'CCNET__Database__DB': 'ccnet_db',
    'CCNET__Database__CONNECTION_CHARSET': 'utf8',

    'SEAFDAV__WEBDAV__enabled': 'false',
    'SEAFDAV__WEBDAV__port': '8080',
    'SEAFDAV__WEBDAV__share_name': '/seafdav',

    'SEAFEVENTS__DATABASE__type': 'mysql',
    # No default value for SEAFEVENTS__DATABASE__host
    'SEAFEVENTS__DATABASE__port': '3306',
    # TODO: Use root or create database user before running this script?
    'SEAFEVENTS__DATABASE__username': 'root',
    # No default value for SEAFEVENTS__DATABASE__password
    'SEAFEVENTS__DATABASE__name': 'seahub_db',

    # Spaces in section names are encoded with '0x20' (HEX representation of a space character)
    # This is inspired by Gitea, which uses 0x2E for a dot character
    'SEAFEVENTS__SEAHUB0x20EMAIL__enabled': 'true',
    'SEAFEVENTS__SEAHUB0x20EMAIL__interval': '30m',
    'SEAFEVENTS__STATISTICS__enabled': 'true',
    'SEAFEVENTS__AUDIT__enabled': 'true',
    'SEAFEVENTS__INDEX0x20FILES__external_es_server': 'true',
    'SEAFEVENTS__INDEX0x20FILES__es_host': 'elasticsearch',
    'SEAFEVENTS__INDEX0x20FILES__es_port': '9200',
    'SEAFEVENTS__INDEX0x20FILES__enabled': 'true',
    'SEAFEVENTS__INDEX0x20FILES__interval': '10m',
    'SEAFEVENTS__INDEX0x20FILES__highlight': 'fvh',
    'SEAFEVENTS__INDEX0x20FILES__index_office_pdf': 'true',
    'SEAFEVENTS__FILE0x20HISTORY__enabled': 'true',
    'SEAFEVENTS__FILE0x20HISTORY__suffix': 'md,txt,doc,docx,xls,xlsx,ppt,pptx,sdoc',

    'SEAFILE__fileserver__port': '8082',
    'SEAFILE__database__type': 'mysql',
    # No default value for SEAFILE__database__host
    'SEAFILE__database__port': '3306',
    # TODO: Use root or create database user before running this script?
    'SEAFILE__database__user': 'root',
    # No default value for SEAFILE__database__password
    'SEAFILE__database__db_name': 'seafile_db',
    'SEAFILE__database__connection_charset': 'utf8',
    'SEAFILE__notification__enabled': 'false',
    'SEAFILE__notification__host': '127.0.0.1',
    'SEAFILE__notification__port': '8083',
    'SEAFILE__notification__log_level': 'info',
    # No default value for jwt_private_key: should be created outside the container and passed in via ENV
}

def generate_conf_file(path: str, prefix: str):
    # TODO: Explain parameters
    # Get all matching variables from "DEFAULT_VALUES"
    variables = {key: value for key, value in DEFAULT_VALUES.items() if key.startswith(prefix)}

    # Get matching environment variables
    user_variables = {key: value for key, value in os.environ.items() if key.startswith(prefix)}

    # Update variables, values supplied by the user take precedence
    variables.update(user_variables)

    # TODO: Check that required ENV (e.g. database password) are set, exit with non-zero exit code if not

    config = configparser.ConfigParser()

    for key, value in variables.items():
        parts = key.split('__')

        if len(parts) != 3:
            logger.error('Error: Variable "%s" does not match PREFIX__SECTION__KEY format', key)
            sys.exit(1)

        # Spaces in section names are encoded with '0x20' (HEX representation of a space character)
        # This is inspired by Gitea, which uses 0x2E for a dot character
        section = parts[1].replace('0x20', ' ')
        key = parts[2]

        if section not in config:
            # section does not exist yet
            config[section] = {}

        config[section][key] = value

    if not os.path.exists(path):
        logger.info(f'Generating {os.path.basename(path)} since it does not exist yet')
    else:
        logger.info(f'Updating {os.path.basename(path)}')

    with open(path, 'w') as file:
        config.write(file)

def generate_gunicorn_config_file(path: str):
    # TODO: Can pids_dir be hardcoded? It was dynamic in setup-seafile-mysql.py

    # Source: https://github.com/haiwen/seafile-docker/blob/da9bf740e4a093a0c25c4ae9a09e08069194fc73/scripts/scripts_11.0/setup-seafile-mysql.py#L1213
    config = """
import os

daemon = True
workers = 5

# default localhost:8000
bind = "127.0.0.1:8000"

# Pid
pids_dir = '/opt/seafile/pids'
pidfile = os.path.join(pids_dir, 'seahub.pid')

# for file upload, we need a longer timeout value (default is only 30s, too short)
timeout = 1200

limit_request_line = 8190
"""

    if not os.path.exists(path):
        logger.info(f'Generating {os.path.basename(path)} since it does not exist yet')
    else:
        logger.info(f'Updating {os.path.basename(path)}')

    with open(path, 'w') as file:
        # Use lstrip() to remove leading whitespace
        file.write(config.lstrip())

if __name__ == '__main__':
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

    generate_conf_file(path=CCNET_CONF_PATH, prefix='CCNET__')
    generate_conf_file(path=SEAFDAV_CONF_PATH, prefix='SEAFDAV__')
    generate_conf_file(path=SEAFEVENTS_CONF_PATH, prefix='SEAFEVENTS__')
    generate_conf_file(path=SEAFILE_CONF_PATH, prefix='SEAFILE__')

    generate_gunicorn_config_file(path=GUNICORN_CONF_PATH)
    # TODO: Generate seahub_settings.py
