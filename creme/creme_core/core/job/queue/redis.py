################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2022  Hybird
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
import traceback
from functools import wraps
from time import sleep
from uuid import uuid1

from django.utils.translation import gettext_lazy as _
from redis import Redis
from redis.exceptions import RedisError

from creme.creme_core.utils.serializers import json_encode

from .base import BaseJobSchedulerQueue, Command

logger = logging.getLogger(__name__)


def _redis_errors_2_bool(f):
    @wraps(f)
    def _aux(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except RedisError as e:
            logger.critical('Error when sending command to Redis [%s]', e)
            return True

        return False

    return _aux


# NB: we do not need to build a reliable redis queue (see http://redis.io/commands/rpoplpush )
#     because the only reliable data come from our RDBMS; Redis is just used an
#     event broker. If there is a crash, the jobs list is rebuilt from the RDBMS.

# TODO: pub-sub allows to watch the numbers of readers -> use it to (re-)launch the command ?
class RedisQueue(BaseJobSchedulerQueue):
    verbose_name = _('Redis queue')
    JOBS_COMMANDS_KEY = 'creme_jobs'
    JOBS_PONG_KEY_PREFIX = 'creme_jobs_pong'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._redis = Redis.from_url(self.setting)

    def clear(self):
        self._redis.delete(self.JOBS_COMMANDS_KEY)
        # print(dir(self._redis))

    @_redis_errors_2_bool
    def start_job(self, job):
        logger.info('Job scheduler queue: request START "%s"', job)
        self._redis.lpush(self.JOBS_COMMANDS_KEY, f'{Command.START}-{job.id}')

    def end_job(self, job):  # TODO: factorise
        logger.info('Job scheduler queue: request END "%s"', job)
        self._redis.lpush(self.JOBS_COMMANDS_KEY, f'{Command.END}-{job.id}')

    @_redis_errors_2_bool
    def refresh_job(self, job, data):  # TODO: factorise
        logger.info('Job scheduler queue: request REFRESH "%s" (data=%s)', job, data)
        self._redis.lpush(
            self.JOBS_COMMANDS_KEY,
            f'{Command.REFRESH}-{job.id}-{json_encode(data)}'
        )

    def get_command(self, timeout):
        # NB: can raise RedisError (ConnectionError, TimeoutError, other ?!)
        # TODO: wrap in _BaseJobSchedulerQueue.Error ??

        cmd = None
        result = self._redis.brpop(self.JOBS_COMMANDS_KEY, timeout)

        if result is not None:  # None == timeout
            # NB: result == (self.JOBS_KEY, command)
            try:
                cmd_type, data = result[1].decode().split('-', 1)
                cmd = Command.build(cmd_type, data)
            except Exception:
                logger.warning(
                    'Job scheduler queue: invalid command "%s"\n%s',
                    result, traceback.format_exc(),
                )

        return cmd

    def ping(self):
        value = str(uuid1())
        logger.info('Job scheduler queue: request PING id="%s"', value)
        _redis = self._redis
        pong_result = None

        try:
            _redis.ping()
            _redis.lpush(self.JOBS_COMMANDS_KEY, f'{Command.PING}-{value}')

            # TODO: meh. Use a push/pull method instead of polling ?
            for i in range(3):
                sleep(1)
                pong_result = _redis.get(self._build_pong_key(value))

                if pong_result is not None:
                    break
        except RedisError as e:
            return self._queue_error(f'{e.__module__}.{e.__class__}: {e}')

        if pong_result is None:
            return str(self._manager_error)

    def _build_pong_key(self, ping_value):
        return f'{self.JOBS_PONG_KEY_PREFIX}-{ping_value}'

    def pong(self, ping_cmd):
        # NB: '1' has no special meaning, because only the existence of the key is used.
        # TODO: '10' in settings ?
        self._redis.setex(self._build_pong_key(ping_cmd.data_id), value=1, time=10)
