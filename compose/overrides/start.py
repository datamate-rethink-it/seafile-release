#!/usr/bin/env python3
#coding: UTF-8

"""
Starts the seafile/seahub server and watches the controller process. It is
the entrypoint command of the docker container.
"""

import json
import os
from os.path import exists, dirname, join
import sys
import time

from utils import (
    call, get_conf, get_install_dir, get_script, get_command_output,
    wait_for_mysql, setup_logging
)
from upgrade import check_upgrade
from bootstrap import init_seafile_server


shared_seafiledir = '/shared/seafile'
ssl_dir = '/shared/ssl'
generated_dir = '/bootstrap/generated'
installdir = get_install_dir()
topdir = dirname(installdir)

def watch_controller():
    maxretry = 4
    retry = 0
    while retry < maxretry:
        controller_pid = get_command_output('ps aux | grep seafile-controller | grep -v grep || true').strip()
        garbage_collector_pid = get_command_output('ps aux | grep /scripts/gc.sh | grep -v grep || true').strip()
        if not controller_pid and not garbage_collector_pid:
            retry += 1
        else:
            retry = 0
        time.sleep(5)
    print('seafile controller exited unexpectedly.')
    sys.exit(1)

def main():
    if not exists(shared_seafiledir):
        os.mkdir(shared_seafiledir)
    if not exists(generated_dir):
        os.makedirs(generated_dir)

    check_upgrade()
    os.chdir(installdir)

    # seahub requires conf/admin.txt in order to create an admin user
    # TODO: Create a PR to read from environment variables instead
    # https://github.com/haiwen/seahub/blob/20cf8b7f5897a89c695bdb01a066a3fbdbfece9c/scripts/check_init_admin.py#L344
    admin_pw = {
        'email': get_conf('SEAFILE_ADMIN_EMAIL', 'me@example.com'),
        'password': get_conf('SEAFILE_ADMIN_PASSWORD', 'asecret'),
    }
    password_file = join(topdir, 'conf', 'admin.txt')
    with open(password_file, 'w') as fp:
        json.dump(admin_pw, fp)


    try:
        non_root = os.getenv('NON_ROOT', default='') == 'true'
        if non_root:
            call('su seafile -c "{} start"'.format(get_script('seafile.sh')))
            call('su seafile -c "{} start"'.format(get_script('seahub.sh')))
        else:
            call('{} start'.format(get_script('seafile.sh')))
            call('{} start'.format(get_script('seahub.sh')))
    finally:
        if exists(password_file):
            os.unlink(password_file)

    print('seafile server is running now.')
    try:
        watch_controller()
    except KeyboardInterrupt:
        print('Stopping seafile server.')
        sys.exit(0)

if __name__ == '__main__':
    setup_logging()
    main()
