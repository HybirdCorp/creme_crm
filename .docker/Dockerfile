# Download base image ubuntu 18.04
FROM ubuntu:latest

# LABEL about the custom image
LABEL maintainer="ffabre@hybird.org"
LABEL version="0.1"
LABEL description="Creme Docker Image"

# Disable Prompt During Packages Installation
ARG DEBIAN_FRONTEND=noninteractive

# Update Ubuntu Software repository
RUN apt update

# Install the base packages
RUN apt install -y git curl dirmngr apt-transport-https lsb-release ca-certificates
RUN apt install -y g++ gcc make python3 python3-dev python3-pip virtualenv sqlite3

# Install nodejs
RUN curl -sL https://deb.nodesource.com/setup_12.x | bash -
RUN apt install -y nodejs

# Install databases
# RUN apt install -y postgresql postgresql-client

# Create users for django server
RUN useradd -ms /bin/bash creme

# Setup postgresql
# USER postgres
# RUN /etc/init.d/postgresql start &&\
#    psql --command "CREATE USER creme WITH SUPERUSER PASSWORD 'creme';"

# Swith to user "creme"
USER creme
RUN mkdir /home/creme/src/
WORKDIR /home/creme/src/

# Build virtualenv
RUN virtualenv -p $(which python3) /home/creme/.virtualenvs/creme-docker

# Setup bashrc
COPY bashrc /home/creme/.bashrc.docker
COPY postactivate /home/creme/.virtualenvs/creme-docker/bin/postactivate
RUN echo ". /home/creme/.bashrc.docker" >> /home/creme/.bashrc
