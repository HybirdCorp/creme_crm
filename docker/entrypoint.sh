#!/bin/bash

set -eux

export DJANGO_SETTINGS_MODULE=docker_settings


case "${CREME_DATABASE_ENGINE-}" in
    django.db.backends.postgresql)
        wait-for-it "$CREME_DATABASE_HOST:$CREME_DATABASE_PORT" -t 15;;
    django.db.backends.mysql)
        wait-for-it "$CREME_DATABASE_HOST:$CREME_DATABASE_PORT" -t 15;;
esac

creme migrate;
creme creme_populate;
creme check;
supervisord --configuration /srv/creme/supervisord.conf;
