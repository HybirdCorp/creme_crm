# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2021  Hybird
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

from json import loads as json_load
from typing import Optional

from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from creme.creme_core.models import Job


# CMD_START   = 'START'
# CMD_END     = 'END'
# CMD_REFRESH = 'REFRESH'
# CMD_PING    = 'PING'
class Command:
    START   = 'START'
    END     = 'END'
    REFRESH = 'REFRESH'
    PING    = 'PING'

    def __init__(self, cmd_type: str, data_id=None, data=None):
        # self.type = cmd_type  # see CMD_*
        self.type = cmd_type  # START/END/REFRESH/PING
        self.data_id = data_id
        self.data = data

    @classmethod
    def _build_START_command(cls, data) -> 'Command':
        return cls(cmd_type=cls.START, data_id=int(data))

    @classmethod
    def _build_END_command(cls, data) -> 'Command':
        return cls(cmd_type=cls.END, data_id=int(data))

    @classmethod
    def _build_REFRESH_command(cls, data) -> 'Command':
        job_id, refresh_data = data.split('-', 1)

        return cls(
            cmd_type=cls.REFRESH,
            data_id=int(job_id),
            data=json_load(refresh_data),
        )

    @classmethod
    def _build_PING_command(cls, data) -> 'Command':
        return cls(cmd_type=cls.PING, data_id=data)

    @classmethod
    def build(cls, cmd_type, data) -> 'Command':
        method = getattr(cls, f'_build_{cmd_type}_command', None)
        if method is None:
            raise ValueError(f'The command type "{cmd_type}" is invalid.')

        return method(data)


# class _BaseJobSchedulerQueue:
class BaseJobSchedulerQueue:
    verbose_name = 'Abstract queue'  # Override me
    # _main_queue = None
    _manager_error = _(
        'The job manager does not respond.\n'
        'Please contact your administrator.'
    )

    def __init__(self, setting: str):
        self.setting = setting

    @classmethod
    def _queue_error(cls, msg):
        return gettext(
            'There is a connection error with the job manager.\n'
            'Please contact your administrator.\n'
            '[Original error from «{queue}»:\n{message}]'
        ).format(
            queue=cls.verbose_name,
            message=msg,
        )

    def clear(self):
        raise NotImplementedError

    def destroy(self):
        """Call it of the server side when quitting to clean resources."""
        pass

    # @classmethod
    # def get_main_queue(cls):
    #     if cls._main_queue is None:
    #         cls._main_queue = cls()
    #
    #     return cls._main_queue

    def start_job(self, job: Job) -> bool:
        """Send a command to start the given Job.
        Abstract method ; should be overloaded.
        Overloading method should not raise exception, and raise 'False' instead.
        @param job: Instance of creme_core.models.Job.
        @return Boolean ; 'True' means 'error'.
        """
        raise NotImplementedError

    def end_job(self, job: Job):
        "@param job: Instance of creme_core.models.Job"
        raise NotImplementedError

    def refresh_job(self, job: Job, data: dict) -> bool:
        """The setting of the Job have changed (periodicity, enabled...).
        Abstract method ; should be overridden.
        Overriding method should not raise exception, and raise 'False' instead.
        @param job: Instance of creme_core.models.Job.
        @param data: JSON-compliant dictionary containing new values for fields.
        @return Boolean ; 'True' means 'error'.
        """
        raise NotImplementedError

    # def stop_job(self, job): TODO ?

    def get_command(self, timeout):
        """Retrieved the sent command.
        @param timeout: Integer, in seconds.
        @return: An instance of Command or None (which means "time out").
                 The command's type is in {CMD_START, CMD_END, CMD_REFRESH, CMD_PING}.
                 The command's id is the related Job's id, excepted for the command CMD_PING,
                 where it is a string which should be given to the pong() method.
                 The command's data is only for CMD_REFRESH (dictionary with new values).
        """
        raise NotImplementedError

    def ping(self) -> Optional[str]:
        """ Check if the queue & the job manager are running.
        @return Returns an error string, or 'None'.
        """
        raise NotImplementedError

    # def pong(self, ping_value):
    def pong(self, ping_cmd: Command):
        raise NotImplementedError
