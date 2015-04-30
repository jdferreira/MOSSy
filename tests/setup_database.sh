#!/usr/bin/env bash

# Make sure that a user named owltosql exists that has password owltosql
# and that has all privileges on the owltosql database
#
# For the record, this is done using the follwing commands in mysql, logged in
# as root:
#
# CREATE USER owltosql@localhost IDENTIFIED BY "owltosql";
# GRANT ALL ON owltosql.* TO owltosql@localhost;
#
# Do *NOT* create the database "owltosql". OWLtoSQL depends on the database not
# existing to work correctly.

cd "$(dirname $0)"

BASE="$HOME/Dropbox/Projects/OWLtoSQL"
LIB="$BASE/lib"

OWLSQL="$BASE/jars/owlsql.jar"
OWLAPI="$BASE/lib/owlapi/owlapi-3.4.8.jar"
MYSQL="$BASE/lib/mysql/mysql-connector-java-5.1.31-bin.jar"
GSON="$BASE/lib/gson/gson-2.2.4.jar"
DIFFUTILS="$BASE/lib/diffutils/diffutils-1.2.1.jar"

export CLASSPATH="$OWLSQL:$OWLAPI:$MYSQL:$GSON:$DIFFUTILS"

java pt.owlsql.Application "$@"
