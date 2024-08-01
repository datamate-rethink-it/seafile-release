#!/usr/bin/env python3

import configparser
import os

CONFIG_DIR = '/shared/seafile/conf'
SEAFILE_CONF_PATH = os.path.join(CONFIG_DIR, 'seafile.conf')

# Specify default values
# Note: configparser only allows strings as values
DEFAULT_VALUES = {
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

def generate_seafile_conf():
    prefix = 'SEAFILE__'

    # Get all matching variables from "DEFAULT_VALUES"
    variables = {key: value for key, value in DEFAULT_VALUES.items() if key.startswith(prefix)}

    # Get matching environment variables
    user_variables = get_environment_variables(prefix=prefix)

    # Update: user-supplied variables take precedence
    variables.update(user_variables)

    # TODO: Refactor this out into a reusable function
    config = configparser.ConfigParser()

    for key, value in variables.items():
        parts = key.split('__')

        if len(parts) != 3:
            # TODO: Print error, does not match format PREFIX__section__key
            os.exit(1)

        section = parts[1]
        key = parts[2]

        if section not in config:
            # section does not exist yet
            config[section] = {}

        config[section][key] = value

    # TODO: Update path to write actual config file
    with open('example.ini', 'w') as file:
        config.write(file)

def get_environment_variables(prefix: str):
    # Return all environment variables that start with "$prefix"
    return {key: value for key, value in os.environ.items() if key.startswith(prefix)}

if __name__ == '__main__':
    # TODO
    # generate_seahub_settings()
    generate_seafile_conf()
