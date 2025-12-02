# syntax = docker/dockerfile:1.3

FROM python:3.13-slim-trixie as creme-demo

SHELL ["/bin/bash", "-c"]

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV PYTHONUNBUFFERED 1

WORKDIR /srv/creme

RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt \
    set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        wait-for-it \
        libpq-dev \
        libmariadb-dev \
        libcairo-dev \
        build-essential;

RUN useradd --shell /bin/bash --uid 1001 creme_user
RUN chown -R creme_user /srv

USER creme_user

COPY docker/docker_settings.py /srv/creme/docker_settings.py
ENV DJANGO_SETTINGS_MODULE docker_settings


RUN --mount=type=bind,source=.,target=/tmp/src \
    --mount=type=cache,target=/srv/creme/.cache,uid=1001 \
    set -eux; \
    mkdir -p /srv/creme/logs; \
    mkdir -p /srv/creme/data; \
    cp -r /tmp/src /srv/creme/src; \
    python3 -m venv /srv/creme/venv; \
    /srv/creme/venv/bin/pip install --cache-dir=/srv/creme/.cache/pip --upgrade pip setuptools wheel; \
    /srv/creme/venv/bin/pip install --cache-dir=/srv/creme/.cache/pip /srv/creme/src[mysql,pgsql]; \
    /srv/creme/venv/bin/pip install --cache-dir=/srv/creme/.cache/pip --upgrade uWSGI supervisor; \
    rm -rf /srv/creme/src; \
    /srv/creme/venv/bin/creme generatemedia;

ENV PATH /srv/creme:/srv/creme/venv/bin:$PATH

COPY docker/uwsgi.ini /srv/creme/uwsgi.ini
COPY docker/wsgi.py /srv/creme/wsgi.py

COPY docker/supervisord.conf /srv/creme/supervisord.conf

COPY docker/entrypoint.sh /srv/creme/entrypoint.sh
ENTRYPOINT ["/srv/creme/entrypoint.sh"]

VOLUME /srv/creme/data
EXPOSE 80
