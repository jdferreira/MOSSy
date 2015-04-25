# This module is here only to allow a global cursor object and a lock to ensure
# thread safety

import MySQLdb
import threading

def set_connection(hostname, database, username, password):
    global conn, cursor, lock
    
    conn = MySQLdb.connect(host=hostname, db=database,
                           user=username, passwd=password)
    cursor = conn.cursor()
    lock = threading.Lock()


VALID_START_CHARS = ('abcdefghijklmnopqrstuvwxyz'
                     'ABCDEFGHIJKLMNOPQRSTUVWXYZ_')
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
