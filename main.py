#!/usr/bin/env python3

import argparse
import logging
import sys
import traceback

import mossy.plugins
from mossy import sql, estimate, parse_config


def get_database_params(args):
    
    # Initialize the parameters
    hostname = 'localhost'
    database = username = password = None
    
    if args.sql_config is not None:
        sql_file = args.sql_config
    else:
        try:
            sql_file = open("sql.config")
        except:
            sql_file = None
    
    if sql_file is not None:
        for lineno, line in enumerate(sql_file):
            lineno += 1 # Cause we want lines to start at 1
            
            line = line.rstrip('\n')
            if line.startswith('#') or not line:
                continue
            
            if '=' not in line:
                raise ValueError("{}, l.{}: Missing an equal sign '='."
                                 .format(sql_file.name, lineno))
            
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
                                 .format(sql_file.name, lineno, key))
    
    
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
    if database is None:
        raise Exception("No database provided.")
    if username is None:
        raise Exception("No username provided.")
    if password is None:
        raise Exception("No password provided.")
    
    logging.info("HOSTNAME = %s", hostname)
    logging.info("DATABASE = %s", database)
    logging.info("USERNAME = %s", username)
    logging.info("PASSWORD = %s", password)
    
    return hostname, database, username, password


def main():
    parser = argparse.ArgumentParser(description="Perform semantic similarity "
                                     "based on an OWLtoSQL database.",
                                     add_help=False)
    
    # Help arguments
    parser.add_argument("-?", "--help", action="help",
                        help="Shows this help.")
    
    # Input arguments
    parser.add_argument("config", nargs='*', default=[sys.stdin],
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
    parser.add_argument("-l", "--log", nargs='?', const=sys.stderr,
                        type=argparse.FileType('w'),
                        help="If provided, logging information is printed to "
                             "the selected file. If the flag is provided but "
                             "no file is given, logging information is printed "
                             "into standard error")
    parser.add_argument("-g", "--debug", action="store_const", dest="log_level",
                        default=logging.WARNING, const=logging.DEBUG,
                        help="If provided, the logging facility will output "
                             "any information with log level DEBUG or higher; "
                             "otherwise, only warnings or higher are logged.")
    
    
    # Show time to finish
    parser.add_argument("-t", "--eta", action="store_true",
                        help="If provided show an estimation of how long the "
                             "script will run until it finishes.")
    
    # Database arguments
    parser.add_argument("--sql-config", type=argparse.FileType('r'),
                        default=None,
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
    
    # Setup logging the facility
    if args.log is None:
        logging.basicConfig(handlers=[logging.NullHandler()])
    else:
        logging_format = "%(asctime)s {%(levelname)-7s} %(message)s"
        data_format = "%Y-%m-%d [%H:%M:%S]"
        logging.basicConfig(
            format=logging_format,
            datefmt=data_format,
            level=args.log_level,
            stream=args.log)
    
    # Get the database parameters
    try:
        db_params = get_database_params(args)
    except Exception as e:
        parser.error(e)
    
    # Start a connection to the database
    try:
        sql.set_connection(*db_params)
    except sql.MySQLError as e:
        parser.error(e.args[1])
    
    # Read the configuration file and the extra execution lines provided with
    # the -e flag
    config = parse_config.parse_config(args.config, args.execute)
    
    if args.eta:
        eta = estimate.ETA(config.total, sys.stderr)
        eta.start()
    
    # Run the comparer with the provided items
    for group in config.groups:
        sb = []
        for item in group:
            sb.append("{}".format(item))
        
        group = (config.items[i] for i in group)
        
        try:
            similarity = config.comparer.compare(*group)
        except sql._driver.MySQLError as e:
            raise e
        except Exception as e:
            print("Unable to compare {}".format(", ".join(sb)), file=args.log)
            traceback.print_exception(*sys.exc_info(), file=args.log)
            similarity = float('nan')
        
        sb.append("{:5f}".format(similarity))
        print('\t'.join(sb), file=args.output)
        
        if args.eta:
            eta.increment()
            eta.estimate()
    
    if args.eta:
        eta.finish()


if __name__ == '__main__':
    main()
    
