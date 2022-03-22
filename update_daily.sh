#!/bin/bash

python /django/desidb/manage.py loaddaily -v 3 -a > /django/load-`date -I`.log 2>&1
