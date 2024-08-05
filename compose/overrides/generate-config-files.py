#!/usr/bin/env python3

import configparser
import logging
import os
import sys

from bootstrap import get_proto

logger = logging.getLogger('generate-config-files')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

CONFIG_DIR = '/opt/seafile/conf'
CCNET_CONF_PATH = os.path.join(CONFIG_DIR, 'ccnet.conf')
SEAFDAV_CONF_PATH = os.path.join(CONFIG_DIR, 'seafdav.conf')
SEAFEVENTS_CONF_PATH = os.path.join(CONFIG_DIR, 'seafevents.conf')
SEAFILE_CONF_PATH = os.path.join(CONFIG_DIR, 'seafile.conf')
GUNICORN_CONF_PATH = os.path.join(CONFIG_DIR, 'gunicorn.conf.py')
SEAHUB_SETTINGS_PATH = os.path.join(CONFIG_DIR, 'seahub_settings.py')
NGINX_CONF_PATH = '/shared/nginx/conf/seafile.nginx.conf'

REQUIRED_VARIABLES = [
    'CCNET__Database__HOST',
    'CCNET__Database__PASSWD',
    'SEAFEVENTS__DATABASE__host',
    'SEAFEVENTS__DATABASE__password',
    'SEAFILE__database__host',
    'SEAFILE__database__password',
    'SEAFILE__notification__jwt_private_key',
    'SEAHUB_SECRET_KEY',
    'SEAFILE_SERVER_HOSTNAME',
    # TODO: Should these two environment variable be named differently? Or keep the names for backwards compatibility?
    'DB_HOST',
    'DB_ROOT_PASSWD',
]

# Specify default values
# Note: configparser only allows strings as values
# Note: Uppercase/lowercase matters here
DEFAULT_VALUES = {
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
    # TODO: Set to true (check cdb's commit)
    'SEAFILE__notification__enabled': 'false',
    'SEAFILE__notification__host': '127.0.0.1',
    'SEAFILE__notification__port': '8083',
    'SEAFILE__notification__log_level': 'info',
    # No default value for SEAFILE__notification__jwt_private_key: should be created outside the container and passed in via ENV
}

# Generates a config file
# path is the file location
# prefix is the prefix for environment variables
def generate_conf_file(path: str, prefix: str):
    # Get all matching variables from "DEFAULT_VALUES"
    variables = {key: value for key, value in DEFAULT_VALUES.items() if key.startswith(prefix)}

    # Get matching environment variables
    user_variables = {key: value for key, value in os.environ.items() if key.startswith(prefix)}

    # Update variables, values supplied by the user take precedence
    variables.update(user_variables)

    config = configparser.ConfigParser()

    # Make ConfigParser case sensitive
    # Otherwise it lowercases keys before writing them to a file, but ccnet requires them to be in uppercase (e.g. 'HOST')
    config.optionxform = str

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

def generate_seahub_settings_file(path: str):
    SECRET_KEY = os.environ['SEAHUB_SECRET_KEY']
    SEAFILE_SERVER_HOSTNAME = os.environ['SEAFILE_SERVER_HOSTNAME']
    DB_PASSWORD = os.environ['DB_ROOT_PASSWD']
    DB_HOST= os.environ['DB_HOST']

    database_config_template = """
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '%(name)s',
        'USER': '%(username)s',
        'PASSWORD': '%(password)s',
        'HOST': '%(host)s',
        'PORT': '%(port)s',
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}
"""

    database_config = {
        # TODO: Which values should be configurable through environment variables?
        'name': 'seahub_db',
        # TODO: Use root or create database user before running this script?
        'username': 'root',
        # Use [] to throw if variable is not set
        'password': DB_PASSWORD,
        'host': DB_HOST,
        'port': '3306',
    }

    cache_config_template = """
CACHES = {
    'default': {
        'BACKEND': '%(backend)s',
        'LOCATION': '%(host)s:%(port)s',
    },
    'locmem': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}
"""

    cache_config = {
        # Should use memcached by default
        # TODO: Allow usage of Redis instead of memcached based on environment variables
        # TODO: Host + port should be configurable through environment variables
        'backend': 'django_pylibmc.memcached.PyLibMCCache',
        'host': 'memcached',
        'port': '11211'
    }

    if not os.path.exists(path):
        logger.info(f'Generating {os.path.basename(path)} since it does not exist yet')
    else:
        logger.info(f'Updating {os.path.basename(path)}')

    with open(path, 'w') as file:
        file.writelines([
            "SECRET_KEY = '%s'" % SECRET_KEY, '\n',
            "SERVICE_URL = 'http://%s'" % SEAFILE_SERVER_HOSTNAME, '\n'
        ])

        file.write(database_config_template % database_config)
        file.write(cache_config_template % cache_config)

        file.writelines([
            '\n',
            "COMPRESS_CACHE_BACKEND = 'locmem'\n",
            "TIME_ZONE = '%s'\n" % os.getenv('TIME_ZONE', default='Etc/UTC'),
            "FILE_SERVER_ROOT = '{proto}://{domain}/seafhttp'".format(proto=get_proto(), domain=SEAFILE_SERVER_HOSTNAME),
        ])

def generate_nginx_conf_file(path: str):
    config_template = """
server {
    listen 80;

    server_name %(server_name)s;

    client_max_body_size 10m;

    location / {
        proxy_pass http://127.0.0.1:8000/;
        proxy_read_timeout 310s;
        proxy_set_header Host $http_host;
        proxy_set_header Forwarded "for=$remote_addr;proto=$scheme";
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Connection "";
        proxy_http_version 1.1;

        client_max_body_size 0;
        access_log      /var/log/nginx/seahub.access.log seafileformat;
        error_log       /var/log/nginx/seahub.error.log;
    }

    location /seafhttp {
        rewrite ^/seafhttp(.*)$ $1 break;
        proxy_pass http://127.0.0.1:8082;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size 0;
        proxy_connect_timeout  36000s;
        proxy_read_timeout  36000s;
        proxy_request_buffering off;
        access_log      /var/log/nginx/seafhttp.access.log seafileformat;
        error_log       /var/log/nginx/seafhttp.error.log;
    }

    location /notification/ping {
        proxy_pass http://127.0.0.1:8083/ping;
        access_log      /var/log/nginx/notification.access.log seafileformat;
        error_log       /var/log/nginx/notification.error.log;
    }

    location /notification {
        proxy_pass http://127.0.0.1:8083/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        access_log      /var/log/nginx/notification.access.log seafileformat;
        error_log       /var/log/nginx/notification.error.log;
    }

    location /seafdav {
        proxy_pass         http://127.0.0.1:8080;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Host $server_name;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout  1200s;
        client_max_body_size 0;

        access_log      /var/log/nginx/seafdav.access.log seafileformat;
        error_log       /var/log/nginx/seafdav.error.log;
    }

    location /media {
        root /opt/seafile/seafile-server-latest/seahub;
    }
}
"""

    config = {
        'server_name': os.environ.get('SEAFILE_SERVER_HOSTNAME'),
    }

    if not os.path.exists(path):
        logger.info(f'Generating {os.path.basename(path)} since it does not exist yet')
    else:
        logger.info(f'Updating {os.path.basename(path)}')

    with open(path, 'w') as file:
        # Use lstrip() to remove leading whitespace
        file.write(config_template.lstrip() % config)

if __name__ == '__main__':
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

    # Check that required environment variables are set
    for variable in REQUIRED_VARIABLES:
        if os.environ.get(variable) is None:
            logger.error('Error: Variable "%s" must be provided', variable)
            sys.exit(1)

    generate_conf_file(path=CCNET_CONF_PATH, prefix='CCNET__')
    generate_conf_file(path=SEAFDAV_CONF_PATH, prefix='SEAFDAV__')
    generate_conf_file(path=SEAFEVENTS_CONF_PATH, prefix='SEAFEVENTS__')
    generate_conf_file(path=SEAFILE_CONF_PATH, prefix='SEAFILE__')

    generate_gunicorn_config_file(path=GUNICORN_CONF_PATH)
    generate_seahub_settings_file(path=SEAHUB_SETTINGS_PATH)

    generate_nginx_conf_file(path=NGINX_CONF_PATH)
