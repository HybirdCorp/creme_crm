# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2018  Hybird
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
from datetime import timedelta, datetime, MAXYEAR
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
from ..utils.dates import make_aware_dt
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
            raise _JobTypeRegistry.Error('Invalid job type ID: {}'.format(job.type_id))

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
            raise _JobTypeRegistry.Error("Duplicated job type id: {}".format(job_type.id))

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


class Command(object):
    def __init__(self, cmd_type, data_id=None, data=None):
        self.type = cmd_type  # see CMD_*
        self.data_id = data_id
        self.data = data


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
                        u'[Original error from «{queue}»:\n{message}]').format(
                            queue=cls.verbose_name,
                            message=msg,
        )

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

    def refresh_job(self, job, data):
        """The setting of the Job have changed (periodicity, enabled...).
        Abstract method ; should be overridden.
        Overridding method should not raise exception, and raise 'False' instead.
        @param job: Instance of creme_core.models.Job.
        @param data: JSON-compliant dictionnary containing new values for fields.
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
                 The command's data is only for CMD_REFRESH (dictionnary with new values).
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

        def refresh_job(self, job, data):
            self.refreshed_jobs.append((job, data))
            return False

        def get_command(self, timeout):
            pass  # TODO: use in test

        def ping(self):
            pass

        def pong(self, ping_value):
            pass
else:
    from functools import wraps
    from json import dumps as json_dump, loads as json_load
    # import sys
    import traceback
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


    def _build_start_command(data):
        return Command(cmd_type=CMD_START, data_id=int(data))

    def _build_end_command(data):
        return Command(cmd_type=CMD_END, data_id=int(data))

    def _build_refresh_command(data):
        job_id, refresh_data = data.split('-', 1)

        return Command(cmd_type=CMD_REFRESH, data_id=int(job_id), data=json_load(refresh_data))

    def _build_ping_command(data):
        return Command(cmd_type=CMD_PING, data_id=data)

    COMMANDS = {
        CMD_START:   _build_start_command,
        CMD_END:     _build_end_command,
        CMD_REFRESH: _build_refresh_command,
        CMD_PING:    _build_ping_command,
    }

    # NB: we do not need to build a reliable redis queue (see http://redis.io/commands/rpoplpush )
    #     because the only reliable data come from our RDBMS; Redis is just used an
    #     event broker. If there is a crash, the jobs list is rebuilt from the RDBMS.

    # TODO: should we rely on a watch dog ??
    # TODO: pub-sub allows to watch the numbers of readers -> use it to (re-)launch the command ?
    # TODO: base class -> children: Redis, AMQP, etc...
    class JobManagerQueue(_BaseJobManagerQueue):
        verbose_name = _(u'Redis queue')
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
            self._redis.lpush(self.JOBS_COMMANDS_KEY, '{}-{}'.format(CMD_START, job.id))

        # def stop_job(self, job): TODO: ?

        def end_job(self, job):  # TODO: factorise
            logger.info('Job manager queue: request END "%s"', job)
            self._redis.lpush(self.JOBS_COMMANDS_KEY, '{}-{}'.format(CMD_END, job.id))

        @_redis_errors_2_bool
        def refresh_job(self, job, data):  # TODO: factorise
            logger.info('Job manager queue: request REFRESH "%s" (data=%s)', job, data)
            self._redis.lpush(self.JOBS_COMMANDS_KEY, '{}-{}-{}'.format(CMD_REFRESH, job.id, json_dump(data)))

        def get_command(self, timeout):
            # NB: can raise RedisError (ConnectionError, TimeoutError, other ?!)
            # TODO: wrap in _BaseJobManagerQueue.Error ??

            cmd = None
            result = self._redis.brpop(self.JOBS_COMMANDS_KEY, timeout)

            if result is not None:  # None == timeout
                # NB: result == (self.JOBS_KEY, command)
                try:
                    cmd_type, data = result[1].split('-', 1)
                    cmd = COMMANDS[cmd_type](data)
                except Exception:
                    logger.warn('Job manager queue: invalid command "%s"\n%s',
                                result, traceback.format_exc(),
                               )

            return cmd

        def ping(self):
            value = unicode(uuid1())
            logger.info('Job manager queue: request PING id="%s"', value)
            _redis = self._redis
            pong_result = None

            try:
                _redis.ping()
                _redis.lpush(self.JOBS_COMMANDS_KEY, '{}-{}'.format(CMD_PING, value))

                # TODO: meh. Use a push/pull method instead of polling ?
                for i in xrange(3):
                    sleep(1)
                    pong_result = _redis.get(self._build_pong_key(value))

                    if pong_result is not None:
                        break
            except RedisError as e:
                return self._queue_error(u'{}.{}: {}'.format(
                    e.__module__, e.__class__, e
                ))

            if pong_result is None:
                return unicode(self._manager_error)

        def _build_pong_key(self, ping_value):
            return '{}-{}'.format(self.JOBS_PONG_KEY_PREFIX, ping_value)

        def pong(self, ping_value):
            # NB: '1' has no special meaning, because only the existence of the key is used.
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

        self._system_jobs = []  # Heap, which elements are (wakeup_date, job_instance) => closer wakeup in the first element.
        self._system_jobs_starts = {}
        self._users_jobs = deque()
        self._running_userjob_ids = set()

    class _DeferredJob(object):
        """
        When Creme tries to start a newly created Job, the START command can arrive before the Job instance
        can be retrieved (because of transaction). So we create an instance of DeferredJob, which is inserted
        in the system jobs collections, in order to use the timeout/wakeup code. At wakeup, we try to retrieve
        the related Job ; if it fails again, we use the DeferredJob again, excepted if the numbers of trials
        reaches its limit.
        """
        def __init__(self, job_id):
            self.job_id = job_id
            self.trials = 0

        def next_wakeup(self, now_value):
            self.trials += 1
            # Beware: when the next timeout if below 1 second, the job is run immediately.
            # So we choose a value which is greater, in order to sleep (& so avoid to make
            # all our trials without delay between them).
            return now_value + timedelta(seconds=1.1)

        @property
        def reaches_trials_limit(self):
            return self.trials >= 100

    def _retrieve_jobs(self):
        now_value = now()
        users_jobs = self._users_jobs
        system_jobs = self._system_jobs

        # NB: order_by() => execute users' jobs in the right order (Meta.ordering is already OK, but it could change)
        for job in Job.objects.filter(Q(user__isnull=True) |
                                      Q(user__isnull=False, status=Job.STATUS_WAIT)
                                     ) \
                              .order_by('id'):
            jtype = job.type

            if jtype is None:
                logger.info('JobManager: job id="%s" has an invalid type -> ignored.', job.id)
                continue

            if job.user:
                if jtype.periodic != JobType.NOT_PERIODIC:
                    logger.warn('JobManager: job "%s" is a user job and should be'
                                ' not periodic -> period is ignored.', repr(job),
                               )

                users_jobs.appendleft(job)
            else:  # System jobs
                if jtype.periodic != JobType.NOT_PERIODIC:
                    heappush(system_jobs, (self._next_wakeup(job, now_value), job))
                else:
                    logger.warn('JobManager: job "%s" is a system job and should be'
                                ' (pseudo-)periodic -> job is ignored.', repr(job),
                               )

    def _next_wakeup(self, job, reference_run=None):
        """Computes the next valid wake up, which must be on the form of
        reference_run + N * period, & be > now_value.
        """
        if job.enabled:
            next_wakeup = reference_run or job.reference_run
            now_value = now()
            period = job.real_periodicity.as_timedelta()

            while next_wakeup < now_value:
                next_wakeup += period

            if job.type.periodic == JobType.PSEUDO_PERIODIC:
                dyn_next_wakeup = job.type.next_wakeup(job, now_value)

                if dyn_next_wakeup is not None:
                    next_wakeup = min(next_wakeup, dyn_next_wakeup)
        else:
            # NB: not <month=12, day=31> to avoid overflow
            next_wakeup = make_aware_dt(datetime(year=MAXYEAR, month=1, day=1))

        return next_wakeup

    def _push_user_job(self, user_job):
        users_jobs = self._users_jobs

        if user_job.user:
            # Avoids a possible race condition: the job could be already in the list
            if user_job.id not in (j.id for j in users_jobs):
                users_jobs.appendleft(user_job)
        else:
            logger.warn('JobManager: try to start the job "%s", which is a'
                        ' system job -> command is ignored.', repr(user_job),
                       )

    def _start_job(self, job):
        logger.info('JobManager: start %s', repr(job))

        self._procs[job.id] = python_subprocess('import django; '
                                                'django.setup(); '
                                                'from creme.creme_core.core.job import job_type_registry; '
                                                'job_type_registry({})'.format(job.id)
                                               )

    def _end_job(self, job):
        logger.info('JobManager: end %s', repr(job))
        proc = self._procs.pop(job.id, None)
        if proc is not None:
            proc.wait()  # TODO: use return code ??

    def _handle_kill(self, *args):
        logger.info('Job manager stops: %d running job(s)', len(self._procs))
        exit()

    def _handle_command_end(self, cmd):
        job_id = cmd.data_id

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            logger.warn('JobManager.handle_command_end() -> invalid jod ID: %s', job_id)
        else:
            if job.user:
                self._running_userjob_ids.discard(job.id)
            else:
                if job.type.periodic == JobType.NOT_PERIODIC:
                    logger.critical('JobManager.handle_command_end() -> '
                                    'job "%s" is a system job and should be '
                                    '(pseudo-)periodic -> job is ignored.', repr(job),
                                    )
                else:
                    try:
                        reference_run = self._system_jobs_starts.pop(job.id)
                    except KeyError:
                        logger.warn('JobManager.handle_command_end() ->  try to end '
                                    'the job "%s" which was not started -> command is ignored', repr(job),
                                    )
                    else:
                        if job.enabled:  # Job may have been disabled during its execution
                            heappush(self._system_jobs, (self._next_wakeup(job, reference_run), job))

            self._end_job(job)

    def _handle_command_ping(self, cmd):
        ping_uid = cmd.data_id
        logger.info('JobManager.handle_command_ping() -> PING id "%s"', ping_uid)
        self._queue.pong(ping_uid)

    def _handle_command_refresh(self, cmd):
        job_id = cmd.data_id

        if job_id in self._system_jobs_starts:
            # If the job is running -> the new wake up is computed at the end of its execution ; so we ignore it.
            logger.info('JobManager.handle_command_refresh() -> try to REFRESH the job "%s",'
                        ' which is already running: command is useless.',
                        job_id,
                       )
            return

        system_jobs = self._system_jobs
        job = None

        # Retrieve/remove the job from the heap
        for i, (__, old_job) in enumerate(system_jobs):
            if old_job.id == job_id:
                job = old_job
                del system_jobs[i]
                heapify(system_jobs)
                break
        else:
            logger.warn('JobManager.handle_command_refresh() -> invalid (system) jod ID: %s', job_id)
            return

        try:
            # NB: we do not use the result (which indicates a change, because pseudo-periodic jobs
            #     could need a new wakeup date without change in the job instance.
            job.update(cmd.data)
        except Exception as e:
            logger.warn('JobManager.handle_command_refresh() -> invalid refresh data: %s (%s)', cmd.data, e)
            return

        if not job.enabled:
            logger.warn('JobManager.handle_command_refresh() -> REFRESH job "%s": disabled', repr(job))
            return

        next_wakeup = self._next_wakeup(job)
        heappush(system_jobs, (next_wakeup, job))
        logger.warn('JobManager.handle_command_refresh() -> REFRESH job "%s": next wake up at %s',
                    repr(job), date_format(localtime(next_wakeup), 'DATETIME_FORMAT'),
                   )

    def _handle_command_start(self, cmd):
        job_id = cmd.data_id

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            logger.warn('JobManager.handle_command_start() -> not yet existing jod ID: %s', job_id)
            def_job = self._DeferredJob(job_id=job_id)
            heappush(self._system_jobs, (def_job.next_wakeup(now()), def_job))
        else:
            self._push_user_job(job)

    def start(self, verbose=True):
        logger.info('Job manager starts')

        # TODO: all of this in a function wrapped by a try..except and a loop (+ sleep) which prevents network crashes ?
        # TODO: regularly use Popen.poll() to check if a child has crashed (with a problem which is not a catchable) ?
        self._queue.clear()
        self._retrieve_jobs()

        enable_exit_handler(self._handle_kill)

        users_jobs = self._users_jobs
        system_jobs = self._system_jobs
        system_jobs_starts = self._system_jobs_starts
        running_userjob_ids = self._running_userjob_ids
        now_value = now()

        if verbose:
            if system_jobs:
                print('System jobs:')
                for dt, job in system_jobs:
                    if not job.enabled:
                        print(u' - {job} (id={job_id}) -> disabled'.format(job=job, job_id=job.id))
                    elif dt <= now_value:
                        print(u' - {job} (id={job_id}) -> run immediately'.format(job=job, job_id=job.id))
                    else:
                        print(u' - {job} (id={job_id}) -> next run at {start}'.format(
                                    job=job, job_id=job.id,
                                    start=date_format(localtime(dt), 'DATETIME_FORMAT'),
                                )
                             )
            else:
                print('No system job found.')

            if users_jobs:
                print('User jobs:')
                for job in users_jobs:
                    print(u' - {job} (id={job_id}; user={user})'.format(job=job, job_id=job.id, user=job.user))
            else:
                print('No user job at the moment.')

            print('\nQuit the server with CTRL-BREAK.')

        MAX_USER_JOBS = self._max_user_jobs
        get_handler = {
            CMD_END:     self._handle_command_end,
            CMD_PING:    self._handle_command_ping,
            CMD_REFRESH: self._handle_command_refresh,
            CMD_START:   self._handle_command_start,
        }.get

        while True:
            now_value = now()

            if system_jobs:
                wakeup = system_jobs[0][0]
                timeout = int((wakeup - now_value).total_seconds())

                if timeout < 1:
                    job = heappop(system_jobs)[1]

                    if isinstance(job, self._DeferredJob):
                        try:
                            real_job = Job.objects.get(id=job.job_id)
                        except Job.DoesNotExist:
                            if job.reaches_trials_limit:
                                logger.warn('JobManager: deferred job does not exist after all'
                                            ' its trials (we forget it): %s', job.job_id,
                                           )
                            else:
                                heappush(system_jobs, (job.next_wakeup(now_value), job))
                                logger.warn('JobManager: deferred job still does not exist: %s', job.job_id)
                        else:
                            self._push_user_job(real_job)
                            logger.warn('JobManager: deferred job exists now: %s', real_job.id)
                    else:
                        system_jobs_starts[job.id] = wakeup
                        self._start_job(job)

                    continue  # In order to handle all system jobs which have to be run _now_
            else:
                # No timeout (because we do not need to be woken up by a time-out -- user-jobs are not periodic)
                timeout = 0

            while len(running_userjob_ids) <= MAX_USER_JOBS and users_jobs:
                job = users_jobs.pop()
                self._start_job(job)
                running_userjob_ids.add(job.id)

            cmd = self._queue.get_command(timeout)
            if cmd is None:  # Time out -> time to run a system job
                continue

            cmd_type = cmd.type
            handler = get_handler(cmd_type)

            if handler:
                handler(cmd)
            else:
                logger.warn('JobManager: invalid command TYPE: %s', cmd_type)
