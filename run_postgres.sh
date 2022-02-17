#!/bin/bash

if [ ! -f $POSTGRES_DATA_DIR/PG_VERSION ]; then
    echo "Running initdb in $POSTGRES_DATA_DIR"
    if [ -n "$POSTGRES_PASSWORD" ]; then
        echo $POSTGRES_PASSWORD > $HOME/postgres_password
        POSTGRES_PASSWORD_FILE=$HOME/postgres_password
    fi
    /usr/lib/postgresql/13/bin/initdb -U postgres --pwfile=$POSTGRES_PASSWORD_FILE $POSTGRES_DATA_DIR
    rm -f $HOME/postgres_password
    /usr/lib/postgresql/13/bin/pg_ctl -D $POSTGRES_DATA_DIR start
    # psql --command "CREATE ROLE $POSTGRES_USER PASSWORD '$POSTGRES_PASSWORD' LOGIN CREATEDB"
    # psql --command "CREATE DATABASE $POSTGRES_NAME OWNER $POSTGRES_USER"
    psql --command "CREATE DATABASE $POSTGRES_NAME"
    psql --command "CREATE EXTENSION q3c" $POSTGRES_NAME
    /usr/lib/postgresql/13/bin/pg_ctl -D $POSTGRES_DATA_DIR stop
fi
exec /usr/lib/postgresql/13/bin/postgres -c config_file=/etc/postgresql/13/main/postgresql.conf
