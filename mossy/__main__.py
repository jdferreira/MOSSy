#!/usr/bin/env python3

import argparse
import importlib
import MySQLdb
import os
import parse_config
import sql
import sys
import time
import traceback


def main():
    parser = argparse.ArgumentParser(description="Perform semantic similarity",
                                     add_help=False)
    
    # Help arguments
    parser.add_argument("-?", "--help", action="help",
                        help="Shows this help.")
    
    # Input arguments
    parser.add_argument("config", nargs='*', default=sys.stdin,
                        type=argparse.FileType('r'), metavar="CONFIG",
                        help="A file containing the configuration parameters "
                             "that specify what to compare and how to compare "
                             "it. Multiple files can be given simultaneously, "
                             "which is interpreted as if all files are first "
                             "concatenated and then interpreted.")
    parser.add_argument("-e", "--execute", action="append", default=[],
                        help="Execute the provided line as if it comes from "
                             "a configuration file.")
    
    # Output arguments
    parser.add_argument("-o", "--output", default=sys.stdout,
                        type=argparse.FileType('w'),
                        help="The file to output the results of this semantic "
                             "similarity request. If not provided, results are "
                             "printed into standard output.")
    parser.add_argument("-l", "--log", nargs='?', type=argparse.FileType('w'),
                        default=sys.stderr, const=sys.stderr,
                        help="If provided, logging information is printed to "
                             "the selected file. If the flag is provided but "
                             "no file is given, logging information is printed "
                             "into standard error")
    # TODO: Add logging capabilities!
    
    # Show time to finish
    parser.add_argument("-t", "--eta", action="store_true",
                        help="If provided show an estimation of how long the "
                             "script will run until it finishes.")
    
    # Database arguments
    parser.add_argument("--sql-config", type=argparse.FileType('r'),
                        default=argparse.FileType('r')('sql.config'),
                        help="The file that contains database accession "
                             "parameters. The file must be of key=value type "
                             "(each key in a line), with the keys 'hostname' "
                             "(optional), 'database', 'username' and "
                             "'password'. If this option is not provided, the "
                             "default value is 'sql.config', which must exist "
                             "in the current directory.")
    parser.add_argument("-h", "--hostname",
                        help="The hostname of the machine that contains the "
                             "MySQL server where the OWLtoSQL database is "
                             "installed. Defaults to 'localhost'")
    parser.add_argument("-d", "--database",
                        help="The name of the MySQL database to connect to.")
    parser.add_argument("-u", "--username",
                        help="The username used to access the database.")
    parser.add_argument("-p", "--password",
                        help="The password associated with the username.")
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Get the SQL parameters
    hostname = database = username = password = None
    if args.sql_config is not None:
        for lineno, line in enumerate(args.sql_config):
            line = line.rstrip('\n')
            if '=' not in line:
                raise ValueError("{}, l.{}: Missing an equal sign '='."
                                 .format(args.sql_config.name, lineno))
            
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            if key == "hostname":
                hostname = value
            elif key == "database":
                database = value
            elif key == "username":
                username = value
            elif key == "password":
                password = value
            else:
                raise ValueError("{}, l.{}: Unexpected key {}."
                                 .format(args.sql_config.name,
                                         lineno, key))
    
    # Overwrite the file configuration with the values from the command line
    if args.hostname is not None:
        hostname = args.hostname
    if args.database is not None:
        database = args.database
    if args.username is not None:
        username = args.username
    if args.password is not None:
        password = args.password
    
    # If no hostname is given, use localhost
    if hostname is None:
        hostname = 'localhost'
    
    # If any of the other parameters is not given, stop execution
    if args.sql_config is None:
        msg = "Missing database parameter: '{}'."
    else:
        msg = "No {} provided. Use the {} flag or add it to '{}'."
    
    if database is None:
        parser.error(msg.format("database", "-d", args.sql_config.name))
    elif username is None:
        parser.error(msg.format("username", "-u", args.sql_config.name))
    if password is None:
        parser.error(msg.format("password", "-p", args.sql_config.name))
    
    # Start a connection to the database
    try:
        sql.set_connection(hostname, database, username, password)
    except Exception as e:
        parser.error(e)
    
    # Import all python files under this directory, recursively
    plugins = os.path.join(os.path.dirname(__file__) or '.', "plugins")
    for filename in os.listdir(plugins):
        if filename.endswith('.py'):
            importlib.import_module("plugins." + filename[:-3])
    
    # Read the configuration file and the extra execution lines provided with
    # the -e flag
    config = parse_config.parse_config(args.config, args.execute)
    
    if args.eta:
        start = time.time()
        count = 0
    
    # Run the comparer with the provided items
    for group in config.groups:
        sb = []
        for item in group:
            sb.append("{}".format(item))
        
        group = (config.items[i] for i in group)
        
        try:
            similarity = config.comparer.compare(*group)
        except MySQLdb.MySQLError as e:
            raise e
        except Exception as e:
            print("Unable to compare {}".format(", ".join(sb)), file=args.log)
            traceback.print_exception(*sys.exc_info(), file=args.log)
            similarity = float('nan')
        
        sb.append("{:5f}".format(similarity))
        print('\t'.join(sb), file=args.output)
        
        if args.eta:
            count += 1
            now = time.time()
            
            todo = config.total - count
            elapsed = now - start
            eta = todo * elapsed / count
            percentage = int(100 * count / config.total)
            
            if eta < 3600: # If we are waiting less tha one hour
                if eta < 60:
                    msg = "{:02}s".format(int(eta))
                else:
                    m, s = divmod(eta, 60)
                    msg = "{:02}m {:02}s".format(int(m), int(s))
            else:
                eta = time.strftime("%Y-%b-%d %H:%M:%S",
                                    time.localtime(now + eta))
                msg = "ETA: {}".format(eta)
            
            # Format a line to print the ETA, ensuring that the previous line
            # gets erased
            print("\r\033[K[{:3}%] {}".format(percentage, msg),
                  file=sys.stderr, end="")
            sys.stderr.flush()
    
    if args.eta:
        elapsed = time.time() - start
        hours, rest = divmod(elapsed, 3600)
        minutes, seconds = divmod(rest, 60)
        
        hours = int(hours)
        minutes = int(minutes)
        seconds = int(seconds)
        
        if hours:
            elapsed = "{:02}h {:02}m {:02}s".format(hours, minutes, seconds)
        elif minutes:
            elapsed = "{:02}m {:02}s".format(minutes, seconds)
        else:
            elapsed = "{:02}s".format(seconds)
        print("\r\033[K[{:3}%] Elapsed: {}".format(percentage, elapsed),
              file=sys.stderr)


if __name__ == '__main__':
    main()
    
