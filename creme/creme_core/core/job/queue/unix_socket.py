# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021-2022  Hybird
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
################################################################################

import logging
import os
import socket
import threading
import traceback
from getpass import getuser
from os import path as os_path
from shutil import rmtree

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext_lazy as _

from creme.creme_core.utils.serializers import json_encode

from .base import BaseJobSchedulerQueue, Command

logger = logging.getLogger(__name__)


class SocketCommand(Command):
    def __init__(self, *args, keep_connection=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.keep_connection = keep_connection
        self.connection = None

    @classmethod
    def _build_PING_command(cls, data):
        return cls(cmd_type=cls.PING, data_id=data, keep_connection=True)


class UnixSocketQueue(BaseJobSchedulerQueue):
    verbose_name = _('Socket queue')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            from socket import AF_UNIX  # NOQA
        except ImportError as e:
            raise ImproperlyConfigured(
                'Job queue: Unix socket is not available on your OS'
            ) from e

        socket_type, base_dir_path = self.setting.split('://', 1)

        if not base_dir_path:
            raise ImproperlyConfigured('Job queue: the path of your unix socket is empty.')

        self._server = None
        self._base_dir_path = base_dir_path
        self._private_dir_path = private = f'{base_dir_path}/private-{getuser()}'
        self._socket_path = f'{private}/socket'

    # TODO: rename in base? (serve()?)
    def clear(self):
        assert self._server is None

        socket_path = self._socket_path
        base_dir_path = self._base_dir_path

        if not os_path.exists(base_dir_path):
            try:
                os.makedirs(base_dir_path, 0o700)
            except os.error as e:
                logger.warning('Cannot create directory %s (%s)', base_dir_path, e)

                raise ImproperlyConfigured(
                    f'Job queue: the directory {base_dir_path} cannot be created.'
                ) from e

        # TODO: check permission instead of delete + re-create ?
        private_dir_path = self._private_dir_path
        if os_path.exists(private_dir_path):
            def _rmtree_error(*args, **kwarg):
                raise ImproperlyConfigured(
                    f'Job queue: cannot clean the socket {socket_path}.'
                )
            rmtree(private_dir_path, onerror=_rmtree_error)

        # TODO: factorise
        try:
            os.mkdir(private_dir_path, 0o700)
        except os.error as e:
            logger.warning('Cannot create directory %s (%s)', private_dir_path, e)

            raise ImproperlyConfigured(
                f'Job queue: the directory {private_dir_path} cannot be created.'
            ) from e

        # TODO: wrap errors?
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(socket_path)
        server.listen()

        self._server = server

    def destroy(self):
        if self._server is not None:
            self._server.close()
            self._server = None
            try:
                os.remove(self._socket_path)
                os.rmdir(self._private_dir_path)
            except OSError:
                pass

    def _client_send(self, msg):
        assert self._server is None

        socket_path = self._socket_path

        if not os_path.exists(socket_path):
            logger.warning(
                'Job scheduler queue: the socket does not exist '
                '(have you launched the scheduler?)',
            )

            return False

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.connect(socket_path)
                client.send(msg.encode('utf-8'))
        except OSError as e:
            logger.critical('Error when sending command to the socket [%s]', e)
            return True

        return False

    def start_job(self, job):
        logger.info('Job scheduler queue: request START "%s"', job)
        return self._client_send(f'{Command.START}-{job.id}')

    def end_job(self, job):
        logger.info('Job scheduler queue: request END "%s"', job)
        self._client_send(f'{Command.END}-{job.id}')

    def refresh_job(self, job, data):
        logger.info('Job scheduler queue: request REFRESH "%s" (data=%s)', job, data)
        return self._client_send(f'{Command.REFRESH}-{job.id}-{json_encode(data)}')

    def get_command(self, timeout):
        assert self._server is not None

        cmd = None
        result = None

        if timeout:
            try:
                self._server.settimeout(timeout)
            except OverflowError:
                pass

        try:
            conn, _addr = self._server.accept()
        except socket.timeout:
            pass
        else:
            data = conn.recv(512)  # NB: should be largely enough

            try:
                cmd_type, data = data.decode('utf-8').split('-', 1)
                cmd = SocketCommand.build(cmd_type, data)
            except Exception:
                logger.warning(
                    'Job scheduler queue: invalid command "%s"\n%s',
                    result, traceback.format_exc(),
                )
            else:
                if cmd.keep_connection:
                    cmd.connection = conn

            if cmd is None or not cmd.keep_connection:
                conn.close()

        return cmd

    def ping(self):
        assert self._server is None

        value = f'{os.getpid()}-{threading.get_ident()}'
        logger.info('Job scheduler queue: request PING id="%s"', value)
        pong_result = None
        socket_path = self._socket_path

        if os_path.exists(socket_path):
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.settimeout(3.0)  # seconds

                try:
                    client.connect(socket_path)
                    client.send(f'{Command.PING}-{value}'.encode('utf-8'))
                    pong_result = client.recv(len(value))
                except socket.timeout:
                    logger.warning('Job scheduler queue: time out on ping')
                except OSError as e:
                    logger.warning('Job scheduler queue: error on ping (%s)', e)
        else:
            logger.warning('Job scheduler queue: socket does not exist')

        if pong_result is None:
            return str(self._manager_error)

    def pong(self, ping_cmd):
        assert isinstance(ping_cmd, SocketCommand) and ping_cmd.connection is not None

        try:
            conn = ping_cmd.connection
            conn.send(ping_cmd.data_id.encode('utf-8'))
            conn.close()
            ping_cmd.connection = None  # Should not be useful...
        except OSError as e:
            logger.warning('Job scheduler queue: error on pong (%s)', e)
