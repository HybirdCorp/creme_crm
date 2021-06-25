# syntax = docker/dockerfile:1.3

FROM python:3.6-buster as creme-demo

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

SHELL ["/bin/bash", "-c"]

ENV PYTHONUNBUFFERED=1
ENV CREME_HOME /home/creme
WORKDIR $CREME_HOME
ENV CREME_VENV "$CREME_HOME/venv"

ARG CREME_INSTALL_MODS

RUN set -eux; \
    apt-get update; \
    apt-get install wait-for-it;

RUN --mount=type=bind,source=.,target=/tmp/src \
    --mount=type=cache,target=/home/creme/.cache \
    set -eux; \
    python3.6 -m venv $CREME_VENV; \
    $CREME_VENV/bin/pip install --cache-dir=/home/creme/.cache/pip --upgrade pip setuptools wheel; \
    $CREME_VENV/bin/pip install --cache-dir=/home/creme/.cache/pip /tmp/src[$CREME_INSTALL_MODS]

ENV PATH $CREME_VENV/bin:$CREME_HOME:$PATH
COPY --chown=creme:creme etc/docker/docker_settings.py docker_settings.py
COPY --chown=creme:creme etc/docker/uwsgi.ini uwsgi.ini
COPY --chown=creme:creme etc/docker/wsgi.py wsgi.py

COPY --chown=creme:creme etc/docker/entrypoint.sh entrypoint.sh
