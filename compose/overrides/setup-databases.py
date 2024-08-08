#!/usr/bin/env python3

import logging
import os
import pymysql
import sys

from os.path import join
from utils import get_install_dir, wait_for_mysql

logger = logging.getLogger('setup-databases')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler(sys.stdout))

CCNET_DB_NAME = 'ccnet_db'
SEAFILE_DB_NAME = 'seafile_db'
SEAHUB_DB_NAME = 'seahub_db'

INSTALL_DIR = get_install_dir()

CCNET_SQL_PATH = join(INSTALL_DIR, 'sql/mysql/ccnet.sql')
SEAFILE_SQL_PATH = join(INSTALL_DIR, 'sql/mysql/seafile.sql')
SEAFEVENTS_SQL_PATH = join(INSTALL_DIR, 'pro/python/seafevents/mysql.sql')
SEAHUB_SQL_PATH = join(INSTALL_DIR, 'seahub/sql/mysql.sql')

def create_database(connection: pymysql.Connection, database: str):
    cursor = connection.cursor()
    sql = f'CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET UTF8'

    try:
        affected_rows = cursor.execute(sql)
    except Exception as e:
        logger.error('Failed to create database %s: %s', database, e)
        sys.exit(1)
    finally:
        cursor.close()

    if affected_rows == 0:
        logger.info('Database "%s" already exists', database)
    elif affected_rows == 1:
        logger.info('Successfully created database "%s"', database)

def import_sql_file(connection: pymysql.Connection, file: str):
    cursor = connection.cursor()

    with open(file, 'r') as fp:
        content = fp.read()

    sqls = [line.strip() for line in content.split(';') if line.strip()]
    for sql in sqls:
        try:
            cursor.execute(sql)
        except Exception as e:
            logger.error('Failed to import "%s": %s', os.path.basename(file), e)
            sys.exit(1)

    connection.commit()

    logger.info('Successfully imported "%s"', os.path.basename(file))

def check_if_table_exists(connection: pymysql.Connection, table_name: str) -> bool:
    cursor = connection.cursor()
    sql = 'SELECT * FROM information_schema.tables WHERE table_schema = DATABASE() AND table_name = %s LIMIT 1'

    try:
        result = cursor.execute(sql, (table_name,))
    except Exception as e:
        logger.error('Could not determine if table "%s" already exists: %s', table_name, e)
        sys.exit(1)
    finally:
        cursor.close()

    return result == 1

if __name__ == '__main__':
    wait_for_mysql()
    logger.info('MariaDB is ready')

    # TODO
    """
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
    """

    host = os.environ['DB_HOST']
    # TODO: Allow port to be customized?
    port = 3306
    user = 'root'
    password = os.environ['DB_ROOT_PASSWD']

    try:
        connection = pymysql.connect(host=host, port=port, user=user, passwd=password)
    except Exception as e:
        if isinstance(e, pymysql.err.OperationalError):
            logger.error('Failed to connect to mysql server using user "%s" and password "***": %s', user, e.args[1])
        else:
            logger.error('Failed to connect to mysql server using user "%s" and password "***": %s', user, e.args[1])
        sys.exit(1)

    databases = [CCNET_DB_NAME, SEAFILE_DB_NAME, SEAHUB_DB_NAME]
    for database in databases:
        create_database(connection, database)

    connection.select_db(CCNET_DB_NAME)
    import_sql_file(connection, CCNET_SQL_PATH)

    connection.select_db(SEAFILE_DB_NAME)
    import_sql_file(connection, SEAFILE_SQL_PATH)

    connection.select_db(SEAHUB_DB_NAME)
    import_sql_file(connection, SEAFEVENTS_SQL_PATH)

    # The "CREATE TABLE" statements inside the seahub .sql file do not contain the
    # "IF NOT EXISTS" statement, so we need to check if a table from the file has
    # already been created before importing the file
    if check_if_table_exists(connection, table_name='abuse_reports_abusereport'):
        logger.info('seahub/sql/mysql.sql is not being imported since the database contains existing tables')
    else:
        import_sql_file(connection, SEAHUB_SQL_PATH)

    connection.close()

    # TODO: Move to other script
    topdir = os.path.dirname(INSTALL_DIR)
    from os.path import exists
    from utils import call
    shared_seafiledir = '/shared/seafile'
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

    # Custom directory for favicon/...
    #gen_custom_dir()

    #loginfo('Updating version stamp')
    #update_version_stamp(os.environ['SEAFILE_VERSION'])

    # non root 
    #non_root = os.getenv('NON_ROOT', default='') == 'true'
    #if non_root:
    #    call('chmod -R a+rwx /shared/seafile/')

