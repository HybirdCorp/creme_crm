################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2021  Hybird
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

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from creme.creme_core.utils.imports import safe_import_object

from .base import BaseJobSchedulerQueue, Command  # NOQA

__queue = None
QUEUE_CLASSES = {
    'redis': 'creme.creme_core.core.job.queue.redis.RedisQueue',
    'unix_socket': 'creme.creme_core.core.job.queue.unix_socket.UnixSocketQueue',
}

if settings.TESTS_ON:
    from .mock import MockQueue

    def get_queue():
        global __queue

        if __queue is None:
            __queue = MockQueue(setting='Unit_tests')

        return __queue
else:
    # TODO: @cache ?
    def get_queue():
        global __queue

        if __queue is None:
            JOBMANAGER_BROKER = settings.JOBMANAGER_BROKER
            broker_type, _broker_adr = JOBMANAGER_BROKER.split('://', 1)
            broker_path = QUEUE_CLASSES.get(broker_type)
            if broker_path is None:
                raise ImproperlyConfigured(
                    f'The setting JOBMANAGER_BROKER is invalid: '
                    f'the broker "{broker_type}" is unknown.'
                )

            broker_cls = safe_import_object(broker_path)
            if broker_cls is None:
                raise ImproperlyConfigured(
                    f'The setting JOBMANAGER_BROKER is invalid: '
                    f'the path "{broker_path}" is invalid.'
                )

            if (
                not isinstance(broker_cls, type)
                or not issubclass(broker_cls, BaseJobSchedulerQueue)
            ):
                raise ImproperlyConfigured(
                    f'The setting JOBMANAGER_BROKER is invalid: '
                    f'{broker_cls} is not a sub-class of <BaseJobSchedulerQueue>.'
                )

            # TODO: wrap errors in ImproperlyConfigured?
            __queue = broker_cls(setting=JOBMANAGER_BROKER)

        return __queue
