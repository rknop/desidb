#!/bin/bash

if [ ! -f $POSTGRES_DATA_DIR/PG_VERSION ]; then
    echo "Running initdb in $POSTGRES_DATA_DIR"
    /usr/lib/postgresql/15/bin/initdb -U postgres --pwfile=${PGPASSWDFILE:-/secrets/pgpasswd} $POSTGRES_DATA_DIR
    /usr/lib/postgresql/15/bin/pg_ctl -D $POSTGRES_DATA_DIR start
    psql --command "CREATE DATABASE desidb OWNER postgres"
    psql --command "CREATE EXTENSION q3c" desidb
    psql --command "CREATE EXTENSION pg_hint_plan" desidb
    ropasswd=`cat ${PGPASSWDFILE_RO:-/secrets/postgres_ro_password}`
    psql --command "CREATE USER desi PASSWORD '${ropasswd}'"
    psql --command "GRANT CONNECT ON DATABASE desidb TO desi"
    psql --command "GRANT USAGE ON SCHEMA public TO desi" desidb
    psql --command "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO desi" desi
    /usr/lib/postgresql/15/bin/pg_ctl -D $POSTGRES_DATA_DIR stop
fi
exec /usr/lib/postgresql/15/bin/postgres -c config_file=/etc/postgresql/15/main/postgresql.conf
