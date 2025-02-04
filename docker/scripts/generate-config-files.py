#!/usr/bin/env python3

import configparser
import json
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
SEAHUB_SETTINGS_OVERRIDES_CONF_PATH = '/tmp/seahub_settings_overrides.py'
SEAFILE_ROLES_PATH = '/tmp/seafile_roles.json'
NGINX_CONF_PATH = '/shared/nginx/conf/seafile.nginx.conf'

CONFIG_FILE_WARNING = '# WARNING: This file will be regenerated on container startup. Any manual changes will be overwritten.\n\n'

REQUIRED_VARIABLES = [
    'SEAFILE__notification__jwt_private_key',
    'SEAHUB__SECRET_KEY',
    'SEAFILE_SERVER_HOSTNAME',
    'DB_HOST',
    'DB_USER',
    'DB_ROOT_PASSWD',
]

# Specify default values
# Note: configparser only allows strings as values
# Note: Uppercase/lowercase matters here
DEFAULT_VALUES = {
    'CCNET__Database__ENGINE': 'mysql',
    'CCNET__Database__HOST': os.environ.get('DB_HOST'),
    'CCNET__Database__PORT': '3306',
    'CCNET__Database__USER': os.environ.get('DB_USER'),
    'CCNET__Database__PASSWD': os.environ.get('DB_ROOT_PASSWD'),
    'CCNET__Database__DB': 'ccnet_db',
    'CCNET__Database__CONNECTION_CHARSET': 'utf8',

    'SEAFDAV__WEBDAV__enabled': 'false',
    'SEAFDAV__WEBDAV__port': '8080',
    'SEAFDAV__WEBDAV__share_name': '/seafdav',

    'SEAFEVENTS__DATABASE__type': 'mysql',
    'SEAFEVENTS__DATABASE__host': os.environ.get('DB_HOST'),
    'SEAFEVENTS__DATABASE__port': '3306',
    'SEAFEVENTS__DATABASE__username': os.environ.get('DB_USER'),
    'SEAFEVENTS__DATABASE__password': os.environ.get('DB_ROOT_PASSWD'),
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
    'SEAFILE__fileserver__use_go_fileserver': 'true',
    'SEAFILE__database__type': 'mysql',
    'SEAFILE__database__host': os.environ.get('DB_HOST'),
    'SEAFILE__database__port': '3306',
    'SEAFILE__database__user': os.environ.get('DB_USER'),
    'SEAFILE__database__password': os.environ.get('DB_ROOT_PASSWD'),
    'SEAFILE__database__db_name': 'seafile_db',
    'SEAFILE__database__connection_charset': 'utf8',
    'SEAFILE__notification__enabled': 'true',
    'SEAFILE__notification__host': '127.0.0.1',
    'SEAFILE__notification__port': '8083',
    'SEAFILE__notification__log_level': 'info',
    # No default value for SEAFILE__notification__jwt_private_key: should be created outside the container and passed in via ENV

    'SEAHUB__SERVICE_URL': f'{get_proto()}://{os.environ.get("SEAFILE_SERVER_HOSTNAME")}',
    'SEAHUB__FILE_SERVER_ROOT': f'{get_proto()}://{os.environ.get("SEAFILE_SERVER_HOSTNAME")}/seafhttp',
    'SEAHUB__TIME_ZONE': os.environ.get('TIME_ZONE', 'Etc/UTC'),
    'SEAHUB__COMPRESS_CACHE_BACKEND': 'locmem',
    'SEAHUB__AVATAR_FILE_STORAGE': 'seahub.base.database_storage.DatabaseStorage',
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
        file.write(CONFIG_FILE_WARNING)
        config.write(file)

def generate_gunicorn_config_file(path: str):
    # Source: https://github.com/haiwen/seafile-docker/blob/da9bf740e4a093a0c25c4ae9a09e08069194fc73/scripts/scripts_11.0/setup-seafile-mysql.py#L1213
    config_template = """
import os

daemon = %(daemon)s
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

    config = {
        # daemon mode must be turned off if logs should go to stdout
        'daemon': os.environ.get('SEAFILE_LOG_TO_STDOUT', 'false').lower() == 'false',
    }

    if not os.path.exists(path):
        logger.info(f'Generating {os.path.basename(path)} since it does not exist yet')
    else:
        logger.info(f'Updating {os.path.basename(path)}')

    with open(path, 'w') as file:
        file.write(CONFIG_FILE_WARNING)

        # Use lstrip() to remove leading whitespace
        file.write(config_template.lstrip() % config)

def generate_seahub_settings_file(path: str):
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
        'name': 'seahub_db',
        'username': os.environ['DB_USER'],
        'password': os.environ['DB_ROOT_PASSWD'],
        'host': os.environ['DB_HOST'],
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

    # Should use memcached as default cache backend
    cache_backend = os.environ.get('SEAHUB__CACHE_BACKEND', 'memcached')
    if cache_backend == 'memcached':
        django_cache_backend = 'django_pylibmc.memcached.PyLibMCCache'
        cache_host = os.environ.get('SEAHUB__CACHE_HOST', 'memcached')
    elif cache_backend == 'redis':
        # TODO: The redis python package is missing from the container image, therefore the redis cache backend does not work!
        django_cache_backend = 'django.core.cache.backends.redis.RedisCache'
        # The redis:// protocol prefix is required
        cache_host = f'redis://{os.environ.get("SEAHUB__CACHE_HOST", "redis")}'
    else:
        logger.error('Error: Invalid value for variable "SEAHUB_CACHE_BACKEND": "%s" (must be "memcached" or "redis")', cache_backend)
        sys.exit(1)

    cache_config = {
        'backend': django_cache_backend,
        'host': cache_host,
        'port': os.environ.get('SEAHUB__CACHE_PORT', '11211'),
    }

    logging_template = """
import sys

LOGGING = {
    'version': 1,
    # Enable existing loggers so that gunicorn errors will be bubbled up when
    # server side error page "Internal Server Error" occurs.
    # ref: https://www.caktusgroup.com/blog/2015/01/27/Django-Logging-Configuration-logging_config-default-settings-logger/
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(format)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue'
        },
    },
    'handlers': {
        'console': {
            'level': '%(level)s',
            # 'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': sys.stdout,
        },
        'default': {
            'level': '%(level)s',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': sys.stdout,
        },
        'onlyoffice_handler': {
            'level': '%(level)s',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
            'stream': sys.stdout,
        },
        'mail_admins': {
            'level': '%(level)s',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        '': {
            'handlers': ['default'],
            'level': '%(level)s',
            'propagate': True
        },
        'django.request': {
            'handlers': ['default', 'mail_admins'],
            'level': '%(level)s',
            'propagate': False
        },
        'py.warnings': {
            'handlers': ['console', ],
            'level': '%(level)s',
            'propagate': False
        },
        'onlyoffice': {
            'handlers': ['onlyoffice_handler', ],
            'level': '%(level)s',
            'propagate': False
        },
    }
}
"""

    logging_config = {
        # TODO: Validate value?
        'level': os.environ.get('SEAFILE_LOG_LEVEL', 'WARNING').upper(),
        'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)s %(funcName)s %(message)s',
    }

    # Generate lines for all the other settings
    lines = []

    # Prefix for environment variables
    prefix = 'SEAHUB__'

    # Get all matching variables from "DEFAULT_VALUES"
    variables = {key: value for key, value in DEFAULT_VALUES.items() if key.startswith(prefix)}

    # Get matching environment variables
    user_variables = {key: value for key, value in os.environ.items() if key.startswith(prefix)}

    # Update variables, values supplied by the user take precedence
    variables.update(user_variables)

    # These variables are handled separately and should not cause auto-generated variable definitions
    excluded_variables = [
        'SEAHUB__CACHE_BACKEND',
        'SEAHUB__CACHE_HOST',
        'SEAHUB__CACHE_PORT',
        # Exclude variables that are lists (for now)
        'SEAHUB__CSRF_TRUSTED_ORIGINS',
        'SEAHUB__ALLOWED_HOSTS',
        'SEAHUB__VIRUS_SCAN_NOTIFY_LIST',
        'SEAHUB__REST_FRAMEWORK_THROTTING_WHITELIST',
    ]

    for key, value in variables.items():
        if key in excluded_variables:
            continue

        # Ignore variables for SAML attribute mapping configuration
        if key.startswith('SEAHUB__SAML_ATTRIBUTE_MAPPING__'):
            continue

        parts = key.split('__')

        if len(parts) != 2:
            logger.error('Error: Variable "%s" does not match PREFIX__KEY format', key)
            sys.exit(1)

        key = parts[1]

        # TODO: Check if key exists in seahub/settings.py to prevent errors due to typos

        # Handle OnlyOffice/Collabora file extension variables
        if key in ['OFFICE_WEB_APP_FILE_EXTENSION', 'OFFICE_WEB_APP_EDIT_FILE_EXTENSION', 'ONLYOFFICE_FILE_EXTENSION', 'ONLYOFFICE_EDIT_FILE_EXTENSION']:
            lines.append(f'{key} = {repr(tuple(value.split(",")))}')
            continue

        # Determine variable type
        if value.lower() in ['true', 'false']:
            # Boolean
            lines.append(f'{key} = {value.lower() == "true"}')
        elif value.isdigit():
            # Number
            lines.append(f'{key} = {value}')
        else:
            # String
            lines.append(f'{key} = "{value}"')

    if not os.path.exists(path):
        logger.info(f'Generating {os.path.basename(path)} since it does not exist yet')
    else:
        logger.info(f'Updating {os.path.basename(path)}')

    with open(path, 'w') as file:
        file.write(CONFIG_FILE_WARNING)

        file.write(database_config_template.lstrip() % database_config)
        file.write(cache_config_template % cache_config)
        file.write('\n')

        file.write(f'CSRF_TRUSTED_ORIGINS = ["{get_proto()}://{os.environ.get("SEAFILE_SERVER_HOSTNAME")}"]\n')

        saml_attribute_mapping = generate_saml_attribute_mapping()
        if len(saml_attribute_mapping) > 0:
            file.write(f'SAML_ATTRIBUTE_MAPPING = {repr(saml_attribute_mapping)}\n')

        if os.environ.get('SEAFILE_LOG_TO_STDOUT', 'false') == 'true':
            file.write(logging_template % logging_config)
            file.write('\n')

        for line in lines:
            file.write(line)
            file.write('\n')

        # Roles can be specified using a JSON file
        if os.path.exists(SEAFILE_ROLES_PATH):
            logger.info('Loading user role definitions from %s into %s...', os.path.basename(SEAFILE_ROLES_PATH), os.path.basename(SEAHUB_SETTINGS_PATH))
            with open (SEAFILE_ROLES_PATH, "r") as roles_file:
                file.writelines([
                    f'\n# Role definitions imported from {os.path.basename(SEAFILE_ROLES_PATH)}:\n',
                    f'ENABLED_ROLE_PERMISSIONS = {repr(json.load(roles_file))}\n',
                ])

        # Allow loading overrides file
        if os.path.exists(SEAHUB_SETTINGS_OVERRIDES_CONF_PATH):
            logger.info('Writing overrides from %s into %s...', os.path.basename(SEAHUB_SETTINGS_OVERRIDES_CONF_PATH), os.path.basename(SEAHUB_SETTINGS_PATH))
            with open (SEAHUB_SETTINGS_OVERRIDES_CONF_PATH, "r") as overrides:
                file.writelines([
                    f'\n# Overrides imported from {os.path.basename(SEAHUB_SETTINGS_OVERRIDES_CONF_PATH)}:\n',
                    overrides.read(),
                ])

def generate_saml_attribute_mapping() -> dict[str, tuple[str]]:
    saml_attribute_mapping = {}

    variables = {key: value for key, value in os.environ.items() if key.startswith('SEAHUB__SAML_ATTRIBUTE_MAPPING__')}

    for key, value in variables.items():
        key = key.removeprefix('SEAHUB__SAML_ATTRIBUTE_MAPPING__')
        saml_attribute_mapping[key] = (value,)

    return saml_attribute_mapping

def generate_nginx_conf_file(path: str):
    config_template = """
# Required for only office document server
map $http_x_forwarded_proto $the_scheme {
    default $http_x_forwarded_proto;
    "" $scheme;
}

map $http_x_forwarded_host $the_host {
    default $http_x_forwarded_host;
    "" $host;
}

map $http_upgrade $proxy_connection {
    default upgrade;
    "" close;
}

server {
    %(listen_ipv6_directive)s
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

    location /onlyofficeds/ {
        # 127.0.0.11 is Docker DNS; explicit DNS resolver is necessary since the upstream is optional
        resolver 127.0.0.11 valid=30s;

        # Variable to prevent "host not found in upstream" error
        set $upstream_onlyoffice onlyoffice;

        # rewrite is necessary; otherwise the path prefix is not stripped if the proxy_pass directive contains variables
        # https://stackoverflow.com/a/71224059
        rewrite /onlyofficeds/(.*) /$1 break;
        proxy_pass http://$upstream_onlyoffice/$1$is_args$args;

        proxy_http_version 1.1;
        client_max_body_size 100M; # Limit Document size to 100MB
        proxy_read_timeout 3600s;
        proxy_connect_timeout 3600s;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $proxy_connection;

        # THIS ONE IS IMPORTANT ! - Subfolder and NO trailing slash !
        proxy_set_header X-Forwarded-Host $the_host/onlyofficeds;

        proxy_set_header X-Forwarded-Proto $the_scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
"""

    if os.environ.get('SEAFILE_LOG_TO_STDOUT', 'false').lower() == 'true':
        config_template = """
# Required for only office document server
map $http_x_forwarded_proto $the_scheme {
    default $http_x_forwarded_proto;
    "" $scheme;
}

map $http_x_forwarded_host $the_host {
    default $http_x_forwarded_host;
    "" $host;
}

map $http_upgrade $proxy_connection {
    default upgrade;
    "" close;
}

server {
    %(listen_ipv6_directive)s
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
        access_log /dev/stdout seafileformat;
        error_log /dev/stdout;
    }

    location /seafhttp {
        rewrite ^/seafhttp(.*)$ $1 break;
        proxy_pass http://127.0.0.1:8082;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        client_max_body_size 0;
        proxy_connect_timeout  36000s;
        proxy_read_timeout  36000s;
        proxy_request_buffering off;
        access_log /dev/stdout seafileformat;
        error_log /dev/stdout;
    }

    location /notification/ping {
        proxy_pass http://127.0.0.1:8083/ping;
        access_log /dev/stdout seafileformat;
        error_log /dev/stdout;
    }

    location /notification {
        proxy_pass http://127.0.0.1:8083/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        access_log /dev/stdout seafileformat;
        error_log /dev/stdout;
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

        access_log /dev/stdout seafileformat;
        error_log /dev/stdout;
    }

    location /media {
        root /opt/seafile/seafile-server-latest/seahub;
    }

    location /onlyofficeds/ {
        # 127.0.0.11 is Docker DNS; explicit DNS resolver is necessary since the upstream is optional
        resolver 127.0.0.11 valid=30s;

        # Variable to prevent "host not found in upstream" error
        set $upstream_onlyoffice onlyoffice;

        # rewrite is necessary; otherwise the path prefix is not stripped if the proxy_pass directive contains variables
        # https://stackoverflow.com/a/71224059
        rewrite /onlyofficeds/(.*) /$1 break;
        proxy_pass http://$upstream_onlyoffice/$1$is_args$args;

        proxy_http_version 1.1;
        client_max_body_size 100M; # Limit Document size to 100MB
        proxy_read_timeout 3600s;
        proxy_connect_timeout 3600s;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $proxy_connection;

        # THIS ONE IS IMPORTANT ! - Subfolder and NO trailing slash !
        proxy_set_header X-Forwarded-Host $the_host/onlyofficeds;

        proxy_set_header X-Forwarded-Proto $the_scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        access_log /dev/stdout seafileformat;
        error_log /dev/stdout;
    }
}
"""

    config = {
        'server_name': os.environ.get('SEAFILE_SERVER_HOSTNAME'),
        'listen_ipv6_directive': 'listen [::]:80;' if os.environ.get('ENABLE_IPV6', 'true').lower() == 'true' else '',
    }

    if not os.path.exists(path):
        logger.info(f'Generating {os.path.basename(path)} since it does not exist yet')
    else:
        logger.info(f'Updating {os.path.basename(path)}')

    with open(path, 'w') as file:
        file.write(CONFIG_FILE_WARNING)

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
