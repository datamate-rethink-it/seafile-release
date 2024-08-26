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
SDOC_DB_NAME = 'sdoc_db'

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

def create_avatars_table(connection: pymysql.Connection):
    cursor = connection.cursor()

    # Docs: https://manual.seafile.com/deploy_pro/deploy_in_a_cluster/#update-seahub-database
    # Note: The "IF NOT EXISTS" was added manually
    sql = 'CREATE TABLE IF NOT EXISTS `avatar_uploaded` (`filename` TEXT NOT NULL, `filename_md5` CHAR(32) NOT NULL PRIMARY KEY, `data` MEDIUMTEXT NOT NULL, `size` INTEGER NOT NULL, `mtime` datetime NOT NULL);'

    try:
        cursor.execute(sql)
    except Exception as e:
        logger.error('Could not create "avatar_uploaded" table: %s', e)
        sys.exit(1)
    finally:
        cursor.close()

if __name__ == '__main__':
    wait_for_mysql()
    logger.info('MariaDB is ready')

    if os.environ.get('CLUSTER_SERVER', 'false').lower() == 'true' and os.environ.get('CLUSTER_MODE') == 'frontend':
        # Database initialization should only run in single-node setups or on the backend node (in case of a cluster setup)
        logger.info('Not initializing database since this node is configured as a frontend node')
        sys.exit(0)

    host = os.environ['DB_HOST']
    # TODO: Allow port to be customized?
    port = 3306
    user = os.environ['DB_USER']
    password = os.environ['DB_ROOT_PASSWD']

    try:
        connection = pymysql.connect(host=host, port=port, user=user, passwd=password)
    except Exception as e:
        if isinstance(e, pymysql.err.OperationalError):
            logger.error('Failed to connect to mysql server using user "%s" and password "***": %s', user, e.args[1])
        else:
            logger.error('Failed to connect to mysql server using user "%s" and password "***": %s', user, e.args[1])
        sys.exit(1)

    databases = [CCNET_DB_NAME, SEAFILE_DB_NAME, SEAHUB_DB_NAME, SDOC_DB_NAME]
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

    create_avatars_table(connection)

    connection.close()
