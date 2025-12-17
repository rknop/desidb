= The Desi Rapid Response Database

See https://desi.lbl.gov/trac/wiki/DESIDatabase

== USAGE

== SCHEMA OVERVIEW


== SETUP

Runs on spin.

=== Database

Postgres server.  Defined in Dockerfile.postgres (and the files referenced therein).  Spin defintion files are in:

  * `spin/desidb-secret.yaml`
  * `spin/desidb-postgres-pvc.yaml`
  * `spin/desidb-postgres.yaml`

**Notes:** After first creating the PVC, you have to uncomment the `initContainers` block in `desidb-postgres.yaml` before apllying that `.yaml` file; otherwise, the permissions on the mounted volume aren't right.  Once this has been done once for a given pvc, you can comment that block back out.

Before trying to migrate the django tables, you have to create the postgres schema by hand.  This isn't something django really understands, I don't believe.

For each schema we need:

```
CREATE SCHEMA <schemaname> AUTHORIZATION postgres;
GRANT SELECT ON SCHEMA <schename> TO desi;
```

=== Djano server

This is mostly for maintaining the database schema.  It is defined in:

  * `spin/desidb-secret.yaml`  (already applied for postgres)
  * `spin/desidb.yaml`

There are a number of django applications defined.  Each release gets its own application.  They all are ideally thin, and inherit from the `db` application; changes are made to the schema, etc., to reflect changes in the data files over time.

== Maintenance

=== Adding releases

==== Creating a new django ap

Underneath `django/desidb`, find the most recent release before the new one, and copy that to the new release:

```
cp -a <recentrelease> <newrelease>
```

Then, cd into <newrelease>.  Delete `migrations/*`, and edit the following files:

* `apps.py` : change the class name, change the `name=` class variable to match the new release
* `models.py` : bulk replace the old release name with the new release name.  *If necessary*, add other customizations so the new release works.
* `management/commands` : rename `load<recentrelease>.py` to `load<newrelease>.py`.  Edit it to import the right models class, and edit all three class variables in `class Command` to point to the right directories and to use the right models.

Add stuff to git as appropriate.

Make sure the place where the django server bind mounts its code (Look for the `django-webap` volume in `spin/desidb.yaml`) has the updated code.  (`git pull` or whatever.)

Restart the django server on spin (scale the deployment to 0 replicas, then back to 1 replica), and check to make sure it started properly.  (If you have errors in your python code, it may fail to start.)


==== After editing the code in any application models

Logged into the django server (via `kubectl --namesapce desidb exec -it <pod> -- /bin/bash`), you have to update the schema migration with:

```
python manage.py makemigrations
```

Then you have to apply the migrations with:

```
python manage.py migrate
```

=== Daily update cron job

There is `spin/desidb-daily-update.yaml` that defines a cron job that looks at the daily spectra from desi and adds them to the daily database.

