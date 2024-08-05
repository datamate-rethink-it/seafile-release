#!/usr/bin/env python3
#coding: UTF-8

## custom changes by datamate:
# writes CSRF_ and SERVICE_URL to seahub_settings.py
# activate notification server later on

"""
Bootstraping seafile server, letsencrypt (verification & cron job).
"""

import argparse
import os
from os.path import exists, dirname, join

from utils import (
    call, get_conf, get_install_dir, loginfo,
    get_script, render_template, get_seafile_version,
    get_version_stamp_file, update_version_stamp,
    read_version_stamp
)

seafile_version = get_seafile_version()
installdir = get_install_dir()
topdir = dirname(installdir)
shared_seafiledir = '/shared/seafile'
ssl_dir = '/shared/ssl'
generated_dir = '/bootstrap/generated'


def gen_custom_dir():
    dst_custom_dir = '/shared/seafile/seahub-data/custom'
    custom_dir = join(installdir, 'seahub/media/custom')
    if not exists(dst_custom_dir):
        os.mkdir(dst_custom_dir)
        call('rm -rf %s' % custom_dir)
        call('ln -sf %s %s' % (dst_custom_dir, custom_dir))


def generate_local_nginx_conf():
    # Now create the final nginx configuratin
    domain = get_conf('SEAFILE_SERVER_HOSTNAME', 'seafile.example.com')
    context = {
        'https': is_https(),
        'domain': domain,
        'is_tmp': False,
    }

    if not os.path.isfile('/shared/nginx/conf/seafile.nginx.conf'):
        render_template(
            '/templates/seafile.nginx.conf.template',
            '/etc/nginx/sites-enabled/seafile.nginx.conf',
            context
        )
        nginx_etc_file = '/etc/nginx/sites-enabled/seafile.nginx.conf'
        nginx_shared_file = '/shared/nginx/conf/seafile.nginx.conf'
        call('mv {0} {1} && ln -sf {1} {0}'.format(nginx_etc_file, nginx_shared_file))

def is_https():
    return get_conf('SEAFILE_SERVER_LETSENCRYPT', 'false').lower() == 'true'

def get_proto():
    proto = 'https' if is_https() else 'http'
    force_https_in_conf = get_conf('FORCE_HTTPS_IN_CONF', 'false').lower() == 'true'
    if force_https_in_conf:
        proto = 'https'
    return proto

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--parse-ports', action='store_true')

    return ap.parse_args()

def init_seafile_server():
    version_stamp_file = get_version_stamp_file()
    if exists(join(shared_seafiledir, 'seafile-data')):
        if not exists(version_stamp_file):
            update_version_stamp(os.environ['SEAFILE_VERSION'])
        # sysbol link unlink after docker finish.
        latest_version_dir='/opt/seafile/seafile-server-latest'
        current_version_dir='/opt/seafile/' + get_conf('SEAFILE_SERVER', 'seafile-server') + '-' +  read_version_stamp()
        if not exists(latest_version_dir):
            call('ln -sf ' + current_version_dir + ' ' + latest_version_dir)
        loginfo('Skip running setup-seafile-mysql.py because there is existing seafile-data folder.')
        return

    loginfo('Now running setup-seafile-mysql.py in auto mode.')
    env = {
        'SERVER_NAME': 'seafile',
        'SERVER_IP': get_conf('SEAFILE_SERVER_HOSTNAME', 'seafile.example.com'),
        'MYSQL_USER': 'root',
        'MYSQL_USER_PASSWD': get_conf('DB_ROOT_PASSWD', ''),
        'MYSQL_USER_HOST': '%',
        'MYSQL_HOST': get_conf('DB_HOST', '127.0.0.1'),
        'MYSQL_PORT': get_conf('DB_PORT', '3306'),
        # Default MariaDB root user has empty password and can only connect from localhost.
        'MYSQL_ROOT_PASSWD': get_conf('DB_ROOT_PASSWD', ''),
    }

    # Change the script to allow mysql root password to be empty
    # call('''sed -i -e 's/if not mysql_root_passwd/if not mysql_root_passwd and "MYSQL_ROOT_PASSWD" not in os.environ/g' {}'''
    #     .format(get_script('setup-seafile-mysql.py')))

    # [sha] The repository contains the patched version of setup-seafile-mysql.py which short-circuits validate_mysql_user_host()/validate_mysql_host()!

    # Change the script to disable check MYSQL_USER_HOST
    #call('''sed -i -e '/def validate_mysql_user_host(self, host)/a \ \ \ \ \ \ \ \ return host' {}'''
    #   .format(get_script('setup-seafile-mysql.py')))

    #call('''sed -i -e '/def validate_mysql_host(self, host)/a \ \ \ \ \ \ \ \ return host' {}'''
    #   .format(get_script('setup-seafile-mysql.py')))

    setup_script = get_script('setup-seafile-mysql.sh')
    call('{} auto -n seafile'.format(setup_script), env=env)

    # return

#     domain = get_conf('SEAFILE_SERVER_HOSTNAME', 'seafile.example.com')
#     proto = get_proto()
#     with open(join(topdir, 'conf', 'seahub_settings.py'), 'a+') as fp:
#         fp.write('\n')
#         fp.write("""CACHES = {
#     'default': {
#         'BACKEND': 'django_pylibmc.memcached.PyLibMCCache',
#         'LOCATION': 'memcached:11211',
#     },
#     'locmem': {
#         'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
#     },
# }
# COMPRESS_CACHE_BACKEND = 'locmem'""")
#         fp.write('\n')
#         fp.write("TIME_ZONE = '{time_zone}'".format(time_zone=os.getenv('TIME_ZONE',default='Etc/UTC')))
#         fp.write('\n')
#         fp.write('FILE_SERVER_ROOT = "{proto}://{domain}/seafhttp"'.format(proto=proto, domain=domain))
#         fp.write('\n')

#         ## CUSTOM: write config to seahub_settings.py ...
#         fp.write('\n')
#         fp.write('CSRF_TRUSTED_ORIGINS = ["{proto}://{domain}"]'.format(proto=proto, domain=domain))
#         fp.write('\n')
#         fp.write('SERVICE_URL = "{proto}://{domain}"'.format(proto=proto, domain=domain))

#     # Disabled the Elasticsearch process on Seafile-container
#     # Connection to the Elasticsearch-container
#     if os.path.exists(join(topdir, 'conf', 'seafevents.conf')):
#         with open(join(topdir, 'conf', 'seafevents.conf'), 'r') as fp:
#             fp_lines = fp.readlines()
#             if '[INDEX FILES]\n' in fp_lines:
#                insert_index = fp_lines.index('[INDEX FILES]\n') + 1
#                insert_lines = ['es_port = 9200\n', 'es_host = elasticsearch\n', 'external_es_server = true\n']
#                for line in insert_lines:
#                    fp_lines.insert(insert_index, line)
#         with open(join(topdir, 'conf', 'seafevents.conf'), 'w') as fp:
#             fp.writelines(fp_lines)

#     # Modify seafdav config
#     if os.path.exists(join(topdir, 'conf', 'seafdav.conf')):
#         with open(join(topdir, 'conf', 'seafdav.conf'), 'r') as fp:
#             fp_lines = fp.readlines()
#             if 'share_name = /\n' in fp_lines:
#                replace_index = fp_lines.index('share_name = /\n')
#                replace_line = 'share_name = /seafdav\n'
#                fp_lines[replace_index] = replace_line

#         with open(join(topdir, 'conf', 'seafdav.conf'), 'w') as fp:
#             fp.writelines(fp_lines)

#     # CUSTOM: activate notification server
#     if os.path.exists(join(topdir, 'conf', 'seafile.conf')):
#         with open(join(topdir, 'conf', 'seafile.conf'), 'r') as fp:
#             fp_lines = fp.readlines()

#         # Flags to track whether we're in the [notification] section and if we've modified the enabled setting
#         in_notification_section = False
#         modified = False

#         # Process each line
#         for i, line in enumerate(fp_lines):
#             if '[notification]' in line:
#                 in_notification_section = True
#             elif in_notification_section and 'enabled = false' in line and not modified:
#                 fp_lines[i] = 'enabled = true\n'
#                 modified = True
#             # If we encounter another section, stop looking for the enabled setting
#             elif in_notification_section and line.startswith('['):
#                 break

#         # Write the modified content back to the file
#         with open(join(topdir, 'conf', 'seafile.conf'), 'w') as fp:
#             fp.writelines(fp_lines)
#     # CUSTOM END

    # After the setup script creates all the files inside the
    # container, we need to move them to the shared volume
    #
    # e.g move "/opt/seafile/seafile-data" to "/shared/seafile/seafile-data"
    files_to_copy = ['conf', 'ccnet', 'seafile-data', 'seahub-data', 'pro-data']
    for fn in files_to_copy:
        src = join(topdir, fn)
        dst = join(shared_seafiledir, fn)
        if not exists(dst) and exists(src):
            call('mv -f ' + str(src) + ' ' + str(dst))
            call('ln -sf ' + str(dst) + ' ' + str(src))

    gen_custom_dir()

    loginfo('Updating version stamp')
    update_version_stamp(os.environ['SEAFILE_VERSION'])

    # non root 
    non_root = os.getenv('NON_ROOT', default='') == 'true'
    if non_root:
        call('chmod -R a+rwx /shared/seafile/')