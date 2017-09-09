# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2017  Hybird
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

from __future__ import print_function

from collections import deque
from heapq import heappush, heappop, heapify
import logging
from uuid import uuid1

from django.conf import settings
from django.db.models import Q
from django.utils.formats import date_format
from django.utils.timezone import now, localtime
from django.utils.translation import ugettext_lazy as _, ugettext, activate

from ..creme_jobs.base import JobType
from ..global_info import set_global_info
from ..models import Job
from ..utils.imports import import_apps_sub_modules
from ..utils.system import python_subprocess, enable_exit_handler


logger = logging.getLogger(__name__)


class _JobTypeRegistry(object):
    class Error(Exception):
        pass

    def __init__(self):
        self._job_types = {}

    def __call__(self, job_id):
        job = Job.objects.get(id=job_id)
        job_type = self.get(job.type_id)

        if job_type is None:
            raise _JobTypeRegistry.Error('Invalid job type ID: %s' % job.type_id)

        # Configure environment
        activate(job.language)
        set_global_info(user=job.user,
                        # usertheme=get_user_theme(request),
                        # per_request_cache={},
                       )

        job_type.execute(job)

    def get(self, job_type_id):
        # return self._job_types.get(job_type_id)
        try:
            return self._job_types[job_type_id]
        except KeyError:
            logger.critical('Unknown JobType: %s', job_type_id)

    def register(self, job_type):
        if self._job_types.setdefault(job_type.id, job_type) is not job_type:
            raise _JobTypeRegistry.Error("Duplicated job type id: %s" % job_type.id)

    def autodiscover(self):
        register = self.register

        for jobs_import in import_apps_sub_modules('creme_jobs'):
            for job in getattr(jobs_import, 'jobs', ()):
                register(job)


job_type_registry = _JobTypeRegistry()
job_type_registry.autodiscover()

CMD_START   = 'START'
CMD_END     = 'END'
CMD_REFRESH = 'REFRESH'
CMD_PING    = 'PING'


class _BaseJobManagerQueue(object):
    verbose_name = 'Abstract queue'  # Overload me
    _main_queue = None
    _manager_error = _(u'The job manager does not respond.\n'
                       u'Please contact your administrator.'
                      )

    @classmethod
    def _queue_error(cls, msg):
        return ugettext(u'There is a connection error with the job manager.\n'
                        u'Please contact your administrator.\n'
                        u'[Original error from «%(queue)s»:\n%(message)s]') % {
                            'queue':   cls.verbose_name,
                            'message': msg,
        }

    def clear(self):
        raise NotImplementedError

    @classmethod
    def get_main_queue(cls):
        if cls._main_queue is None:
            cls._main_queue = cls()

        return cls._main_queue

    def start_job(self, job):
        """Send a command to start the given Job.
        Abstract method ; should be overloaded.
        Overloading method should not raise exception, and raise 'False' instead.
        @param job: Instance of creme_core.models.Job.
        @return Boolean ; 'True' means 'error'.
        """
        raise NotImplementedError

    def end_job(self, job):
        "@param job: Instance of creme_core.models.Job"
        raise NotImplementedError

    def refresh_job(self, job):
        """The setting of the Job have changed (periodicity, enabled...).
        Abstract method ; should be overloaded.
        Overloading method should not raise exception, and raise 'False' instead.
        @param job: Instance of creme_core.models.Job.
        @return Boolean ; 'True' means 'error'.
        """
        raise NotImplementedError

    # def stop_job(self, job): TODO

    def get_command(self, timeout):
        """Retrieved the sent command.
        @param timeout: Integer, in seconds.
        @return: tuple (cmd_type, cmd_data) or None (which means "time out").
                 'cmd_type' is in {CMD_START, CMD_END, CMD_REFRESH, CMD_PING}.
                 'cmd_data' is the related Job's id, excepted for the command CMD_PING, where 'cmd_data'
                 is a string which should be given to the pong() method.
        """
        raise NotImplementedError

    def ping(self):
        """ Check if the queue & the job manager are running.
        @return Returns an error string, or 'None'.
        """
        raise NotImplementedError

    def pong(self, ping_value):
        raise NotImplementedError


if settings.TESTS_ON:
    class JobManagerQueue(_BaseJobManagerQueue):
        "Mocking JobManagerQueue"
        verbose_name = 'Test queue'

        def __init__(self):
            self.started_jobs = []
            self.refreshed_jobs = []

        def clear(self):
            "Useful for test cases ; clear the internal lists."
            self.started_jobs[:] = []
            self.refreshed_jobs[:] = []

        def start_job(self, job):
            self.started_jobs.append(job)
            return False

        def end_job(self, job):
            pass

        def refresh_job(self, job):
            self.refreshed_jobs.append(job)
            return False

        def get_command(self, timeout):
            pass  # TODO: use in test

        def ping(self):
            pass

        def pong(self, ping_value):
            pass
else:
    from functools import wraps
    from time import sleep

    from redis import StrictRedis
    from redis.exceptions import RedisError

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

    # TODO: should we rely on a watch dog ??
    # TODO: pub-sub allows to watch the numbers of readers -> use it to (re-)launch the command ?
    # TODO: base class -> children: Redis, AMQP, etc...
    class JobManagerQueue(_BaseJobManagerQueue):
        verbose_name = _('Redis queue')
        JOBS_COMMANDS_KEY = 'creme_jobs'
        JOBS_PONG_KEY_PREFIX = 'creme_jobs_pong'

        def __init__(self):
            self._redis = StrictRedis.from_url(settings.JOBMANAGER_BROKER)

        def clear(self):
            self._redis.delete(self.JOBS_COMMANDS_KEY)
            # print(dir(self._redis))

        @_redis_errors_2_bool
        def start_job(self, job):
            logger.info('Job manager queue: request START "%s"', job)
            self._redis.lpush(self.JOBS_COMMANDS_KEY, '%s-%s' % (CMD_START, job.id))

        # def stop_job(self, job): TODO: ?

        def end_job(self, job):  # TODO: factorise
            logger.info('Job manager queue: request END "%s"', job)
            self._redis.lpush(self.JOBS_COMMANDS_KEY, '%s-%s' % (CMD_END, job.id))

        @_redis_errors_2_bool
        def refresh_job(self, job):  # TODO: factorise
            logger.info('Job manager queue: request REFRESH "%s"', job)
            self._redis.lpush(self.JOBS_COMMANDS_KEY, '%s-%s' % (CMD_REFRESH, job.id))

        def get_command(self, timeout):
            # NB: can raise RedisError (ConnectionError, TimeoutError, other ?!)
            # TODO: wrap in _BaseJobManagerQueue.Error ??

            result = self._redis.brpop(self.JOBS_COMMANDS_KEY, timeout)

            if result is None:
                return None  # Timeout

            # NB: result == (self.JOBS_KEY, command)
            try:
                cmd_type, job_id = result[1].split('-', 1)

                # TODO: cmd = COMMANDS[cmd_type].cast(...) #KeyError
                if cmd_type != CMD_PING:
                    job_id = int(job_id)
            except ValueError:
                logger.warn('Job manager queue: invalid command "%s"', result)
                return None

            return cmd_type, job_id

        def ping(self):
            value = unicode(uuid1())
            logger.info('Job manager queue: request PING id="%s"', value)
            _redis = self._redis

            try:
                _redis.ping()
                _redis.lpush(self.JOBS_COMMANDS_KEY, '%s-%s' % (CMD_PING, value))

                # TODO: meh. Use a push/pull method instead of polling ?
                for i in xrange(3):
                    sleep(1)
                    pong_result = _redis.get(self._build_pong_key(value))

                    if pong_result is not None:
                        break
            except RedisError as e:
                return self._queue_error(u'%s.%s: %s' % (
                    e.__module__, e.__class__, e
                ))

            if pong_result is None:
                return unicode(self._manager_error)

        def _build_pong_key(self, ping_value):
            return '%s-%s' % (self.JOBS_PONG_KEY_PREFIX, ping_value)

        def pong(self, ping_value):
            # NB: '1' has no special meaning, because the existence of the key is used.
            self._redis.setex(self._build_pong_key(ping_value), value=1, time=10)  # TODO: '10' in settings ?


class JobManager(object):
    """Job scheduler ; it should run it its own process (see 'creme_job_manager'
    command), receive command (START...) from an inter-process queue, and spawn
    jobs in their own process.

    System Jobs & User Jobs are not managed in the same way
        - System Jobs are always run when their periodic time has arrived, so
          there can be as many processes for them than there are enabled system
          Jobs.
        - User jobs are executed with a pool of processes, and its size is given
          by settings.MAX_USER_JOBS.

    If the execution of a (pseudo-)periodic Job takes too long time (more than
    its period), the Job is scheduled to the next valid time, and not executed
    immediately (see _next_wakeup()).

    The "period" of pseudo-periodic is computed each time they are run. But
    the manager runs them regularly (see settings.PSEUDO_PERIOD) in order to
    reduce the aftermath of a redis/... connection problem.
    """
    def __init__(self):
        self._max_user_jobs = settings.MAX_USER_JOBS
        self._queue = JobManagerQueue.get_main_queue()
        self._procs = {}  # key: job.id; value: subprocess.Popen instance

    def _next_wakeup(self, job, now_value, reference_run=None):
        """Computes the next valid wake up, which must be on the form of
        reference_run + N * period, & be > now_value,
        """
        next_wakeup = reference_run or job.reference_run
        period = job.real_periodicity.as_timedelta()

        while next_wakeup < now_value:
            next_wakeup += period

        if job.type.periodic == JobType.PSEUDO_PERIODIC:
            dyn_next_wakeup = job.type.next_wakeup(job, now_value)

            if dyn_next_wakeup is not None:
                next_wakeup = min(next_wakeup, dyn_next_wakeup)

        return next_wakeup

    def _start_job(self, job):
        logger.info('JobManager: start %s', repr(job))

        self._procs[job.id] = python_subprocess('import django; '
                                                'django.setup(); '
                                                'from creme.creme_core.core.job import job_type_registry; '
                                                'job_type_registry(%s)' % job.id
                                               )

    def _end_job(self, job):
        logger.info('JobManager: end %s', repr(job))
        proc = self._procs.pop(job.id, None)
        if proc is not None:
            proc.wait()  # TODO: use return code ??

    def _handle_kill(self, *args):
        logger.info('Job manager stops: %d running job(s)', len(self._procs))
        exit()

    def start(self, verbose=True):
        logger.info('Job manager starts')

        # TODO: all of this in a function wrapped by a try..except and a loop (+ sleep) which prevents network crashes ?
        # TODO: regularly use Popen.poll() to check if a child has crashed (with a problem which is not a catchable) ?
        self._queue.clear()

        system_jobs = []  # Heap
        system_jobs_starts = {}
        users_jobs = deque()
        running_userjob_ids = set()
        now_value = now()

        # NB: order_by() => execute users' jobs in the right order (Meta.ordering is already OK, but it could change)
        for job in Job.objects.filter(Q(user__isnull=True) |
                                      Q(user__isnull=False, status=Job.STATUS_WAIT)
                                     ) \
                              .exclude(enabled=False) \
                              .order_by('id'):
            if job.user:
                if job.type.periodic != JobType.NOT_PERIODIC:
                    logger.warn('JobManager: job "%s" is a user job and should be'
                                ' not periodic -> period is ignored.', repr(job)
                               )

                users_jobs.appendleft(job)
            else:  # System jobs
                if job.type.periodic != JobType.NOT_PERIODIC:
                    heappush(system_jobs, (self._next_wakeup(job, now_value), job))
                else:
                    logger.warn('JobManager: job "%s" is a system job and should be'
                                ' (pseudo-)periodic -> job is ignored.', repr(job)
                               )

        enable_exit_handler(self._handle_kill)

        if verbose:
            if system_jobs:
                print('System jobs:')
                for dt, job in system_jobs:
                    if dt <= now_value:
                        print(u' - %s -> run immediately' % job)
                    else:
                        print(u' - %s -> next run at %s' % (job, date_format(localtime(dt), 'DATETIME_FORMAT')))
            else:
                print('No system job found.')

            if users_jobs:
                print('User jobs:')
                for job in users_jobs:
                    print(u' - %s (user=%s)' % (job, job.user))
            else:
                print('No user job at the moment.')

            print('\nQuit the server with CTRL-BREAK.')

        MAX_USER_JOBS = self._max_user_jobs

        while True:
            now_value = now()

            if system_jobs:
                wakeup = system_jobs[0][0]
                timeout = int((wakeup - now_value).total_seconds())

                if timeout < 1:
                    job = heappop(system_jobs)[1]
                    system_jobs_starts[job.id] = wakeup
                    self._start_job(job)
                    continue  # In order to handle all system jobs which have to be run _now_
            else:
                timeout = 0  # No timeout

            while len(running_userjob_ids) <= MAX_USER_JOBS and users_jobs:
                job = users_jobs.pop()
                self._start_job(job)
                running_userjob_ids.add(job.id)

            cmd = self._queue.get_command(timeout)
            if cmd is None:  # Time out -> time to run a system job
                continue

            cmd_type, job_id = cmd

            if cmd_type == CMD_PING:  # Here job_id is an uuid, not a real Job.id ...
                logger.info('JobManager: PING id "%s"', job_id)
                self._queue.pong(job_id)
                continue

            try:
                job = Job.objects.get(id=job_id)
            except Job.DoesNotExist:
                logger.warn('JobManager: invalid jod ID: %s', job_id)
                continue

            if cmd_type == CMD_START:
                if job.user:
                    # Avoids a possible race condition: the job could be already in the list
                    if job_id not in (job.id for job in users_jobs):
                        users_jobs.appendleft(job)
                else:
                    logger.warn('JobManager: try to start the job "%s", which is a'
                                ' system job -> command is ignored.', repr(job),
                               )
            elif cmd_type == CMD_END:
                if job.user:
                    running_userjob_ids.discard(job.id)
                else:
                    if job.type.periodic == JobType.NOT_PERIODIC:
                        logger.critical('JobManager: job "%s" is a system job and should be'
                                        ' (pseudo-)periodic -> job is ignored.', repr(job),
                                       )
                    else:
                        try:
                            reference_run = system_jobs_starts.pop(job.id)
                        except KeyError:
                            logger.warn('JobManager: try to end the job "%s" which was'
                                        ' not started -> command is ignored', repr(job),
                                       )
                        else:
                            if job.enabled:  # Job may have been disabled during its execution
                                heappush(system_jobs, (self._next_wakeup(job, now_value, reference_run), job))

                self._end_job(job)
            elif cmd_type == CMD_REFRESH:
                if job.user is None:
                    # If the job is running -> the new wake up is computed at
                    # the end of its execution ; so we ignore it.
                    if job.id not in system_jobs_starts:
                        # Remove the job from the heap
                        for i, (__, old_job) in enumerate(system_jobs):
                            if old_job.id == job.id:
                                del system_jobs[i]
                                heapify(system_jobs)
                                break

                        if job.enabled:
                            next_wakeup = self._next_wakeup(job, now_value)
                            heappush(system_jobs, (next_wakeup, job))
                            logger.info('JobManager: refresh job "%s" -> next wake up at %s',
                                        repr(job), date_format(localtime(next_wakeup), 'DATETIME_FORMAT')
                                       )
                        else:
                            logger.info('JobManager: refresh job "%s" -> disabled', repr(job))
                    else:
                        logger.info('JobManager: try to refresh the job "%s", which is'
                                    ' already running -> command is useless.',
                                    repr(job),
                                   )
                else:
                    logger.warn('JobManager: try to refresh the job "%s", which is'
                                ' a not a system job -> command is ignored.',
                                repr(job),
                               )
            else:
                logger.warn('JobManager: invalid command TYPE: %s', cmd_type)
