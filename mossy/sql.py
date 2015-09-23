# This module is here to allow a global cursor object and a lock to ensure
# thread safety. It takes care to select the correct MySQL connector, either
# MySQLdb or PyMySQL, depending on what is installed

import threading

try:
    import MySQLdb as _driver
except ImportError:
    try:
        import pymysql as _driver
    except ImportError:
        raise ImportError("Unable to import either 'MySQLdb' or 'pymysql'")


MySQLError = _driver.MySQLError


def set_connection(hostname, database, username, password):
    global conn, cursor, lock
    
    conn = _driver.connect(host=hostname, db=database,
                           user=username, passwd=password)
    cursor = conn.cursor()
    lock = threading.Lock()


def close_connection():
    global conn, cursor, lock
    cursor.close()
    conn.close()
    
    del conn
    del cursor
    del lock


VALID_START_CHARS = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'
VALID_CHARS = VALID_START_CHARS + '0123456789'

def assert_identifier(identifier):
    # We allow only alphanumeric characters and the underscore character
    # Numbers cannot start the identifeir
    first = True
    for char in identifier:
        if first:
            valid = char in VALID_START_CHARS
            first = False
        else:
            valid = char in VALID_CHARS
        
        if not valid:
            raise Exception("Invalid SQL identifer: '{}'".format(identifer))
