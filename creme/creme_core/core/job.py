# -*- coding: utf-8 -*-

################################################################################
#    Creme is a free/open-source Customer Relationship Management software
#    Copyright (C) 2016-2020  Hybird
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
from collections import deque
from datetime import MAXYEAR, datetime, timedelta
from heapq import heapify, heappop, heappush
from typing import Optional, Set
from uuid import uuid1

from django.conf import settings
from django.db.models import Q
from django.utils.formats import date_format
from django.utils.timezone import localtime, now
from django.utils.translation import activate, gettext
from django.utils.translation import gettext_lazy as _

from ..creme_jobs.base import JobType
from ..global_info import set_global_info
from ..models import Job
from ..utils.dates import make_aware_dt
from ..utils.imports import import_apps_sub_modules
from ..utils.system import enable_exit_handler, python_subprocess

logger = logging.getLogger(__name__)


class _JobTypeRegistry:
    class Error(Exception):
        pass

    def __init__(self):
        self._job_types = {}

    def __call__(self, job_id: int) -> None:
        job = Job.objects.get(id=job_id)
        job_type = self.get(job.type_id)

        if job_type is None:
            raise _JobTypeRegistry.Error(f'Invalid job type ID: {job.type_id}')

        # Configure environment
        activate(job.language)
        set_global_info(user=job.user,
                        # usertheme=get_user_theme(request),
                        # per_request_cache={},
                       )

        job_type.execute(job)

    def get(self, job_type_id: str) -> Optional[JobType]:
        try:
            return self._job_types[job_type_id]
        except KeyError:
            logger.critical('Unknown JobType: %s', job_type_id)

        return None

    def register(self, job_type: JobType) -> None:
        jtype_id = job_type.id

        if not jtype_id:
            raise _JobTypeRegistry.Error(f'Empty JobType id: {job_type}')

        if self._job_types.setdefault(jtype_id, job_type) is not job_type:
            raise _JobTypeRegistry.Error(f"Duplicated job type id: {jtype_id}")

    def autodiscover(self) -> None:
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


class Command:
    def __init__(self, cmd_type, data_id=None, data=None):
        self.type = cmd_type  # see CMD_*
        self.data_id = data_id
        self.data = data


# class _BaseJobManagerQueue:
class _BaseJobSchedulerQueue:
    verbose_name = 'Abstract queue'  # Overload me
    _main_queue = None
    _manager_error = _('The job manager does not respond.\n'
                       'Please contact your administrator.'
                      )

    @classmethod
    def _queue_error(cls, msg):
        return gettext('There is a connection error with the job manager.\n'
                       'Please contact your administrator.\n'
                       '[Original error from «{queue}»:\n{message}]').format(
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

    def pong(self, ping_value):
        raise NotImplementedError


if settings.TESTS_ON:
    # class JobManagerQueue(_BaseJobManagerQueue):
    class JobSchedulerQueue(_BaseJobSchedulerQueue):
        "Mocking JobSchedulerQueue."
        verbose_name = 'Test queue'

        def __init__(self):
            self.started_jobs = []
            self.refreshed_jobs = []

        def clear(self):
            "Useful for test cases ; clear the internal lists."
            self.started_jobs.clear()
            self.refreshed_jobs.clear()

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
    from json import loads as json_load
    import traceback
    from time import sleep

    from redis import StrictRedis  # TODO: "Redis" with redis3
    from redis.exceptions import RedisError

    from creme.creme_core.utils.serializers import json_encode

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
    # class JobManagerQueue(_BaseJobManagerQueue):
    class JobSchedulerQueue(_BaseJobSchedulerQueue):
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
            logger.info('Job scheduler queue: request START "%s"', job)
            self._redis.lpush(self.JOBS_COMMANDS_KEY, f'{CMD_START}-{job.id}')

        # def stop_job(self, job): TODO: ?

        def end_job(self, job):  # TODO: factorise
            logger.info('Job scheduler queue: request END "%s"', job)
            self._redis.lpush(self.JOBS_COMMANDS_KEY, f'{CMD_END}-{job.id}')

        @_redis_errors_2_bool
        def refresh_job(self, job, data):  # TODO: factorise
            logger.info('Job scheduler queue: request REFRESH "%s" (data=%s)', job, data)
            # self._redis.lpush(self.JOBS_COMMANDS_KEY, '{}-{}-{}'.format(CMD_REFRESH, job.id, json_dump(data)))
            self._redis.lpush(self.JOBS_COMMANDS_KEY, f'{CMD_REFRESH}-{job.id}-{json_encode(data)}')

        def get_command(self, timeout):
            # NB: can raise RedisError (ConnectionError, TimeoutError, other ?!)
            # TODO: wrap in _BaseJobSchedulerQueue.Error ??

            cmd = None
            result = self._redis.brpop(self.JOBS_COMMANDS_KEY, timeout)

            if result is not None:  # None == timeout
                # NB: result == (self.JOBS_KEY, command)
                try:
                    cmd_type, data = result[1].decode().split('-', 1)
                    cmd = COMMANDS[cmd_type](data)
                except Exception:
                    logger.warning('Job scheduler queue: invalid command "%s"\n%s',
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
                _redis.lpush(self.JOBS_COMMANDS_KEY, f'{CMD_PING}-{value}')

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

        def pong(self, ping_value):
            # NB: '1' has no special meaning, because only the existence of the key is used.
            self._redis.setex(self._build_pong_key(ping_value), value=1, time=10)  # TODO: '10' in settings ?


# class JobManager:
class JobScheduler:
    """It should run it its own process (see 'creme_job_manager' command),
    receive command (START...) from an inter-process queue, and spawn jobs
    in their own process.

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
        self._queue = JobSchedulerQueue.get_main_queue()
        self._procs = {}  # key: job.id; value: subprocess.Popen instance

        self._system_jobs = []  # Heap, which elements are (wakeup_date, job_instance) => closer wakeup in the first element.
        self._system_jobs_starts = {}
        self._users_jobs = deque()
        self._running_userjob_ids: Set[int] = set()

    class _DeferredJob:
        """
        When Creme tries to start a newly created Job, the START command can arrive before the Job instance
        can be retrieved (because of transaction). So we create an instance of DeferredJob, which is inserted
        in the system jobs collections, in order to use the timeout/wakeup code. At wakeup, we try to retrieve
        the related Job ; if it fails again, we use the DeferredJob again, excepted if the numbers of trials
        reaches its limit.
        """
        job_id: int
        trials: int

        def __init__(self, job_id: int):
            self.job_id = job_id
            self.trials = 0

        def next_wakeup(self, now_value: datetime) -> datetime:
            self.trials += 1
            # Beware: when the next timeout if below 1 second, the job is run immediately.
            # So we choose a value which is greater, in order to sleep (& so avoid to make
            # all our trials without delay between them).
            return now_value + timedelta(seconds=1.1)

        @property
        def reaches_trials_limit(self) -> bool:
            return self.trials >= 100

    def _retrieve_jobs(self) -> None:
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
                logger.info('JobScheduler: job id="%s" has an invalid type -> ignored.', job.id)
                continue

            if job.user:
                if jtype.periodic != JobType.NOT_PERIODIC:
                    logger.warning('JobScheduler: job "%s" is a user job and should be'
                                   ' not periodic -> period is ignored.', repr(job),
                                  )

                users_jobs.appendleft(job)
            else:  # System jobs
                if jtype.periodic != JobType.NOT_PERIODIC:
                    heappush(system_jobs, (self._next_wakeup(job, now_value), job.id, job))
                else:
                    logger.warning('JobScheduler: job "%s" is a system job and should be'
                                   ' (pseudo-)periodic -> job is ignored.', repr(job),
                                  )

    def _next_wakeup(self,
                     job: Job,
                     reference_run: Optional[datetime] = None) -> datetime:
        """Computes the next valid wake up, which must be on the form of
        reference_run + N * period, & be > now_value.
        """
        next_wakeup: datetime

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

    def _push_user_job(self, user_job: Job):
        users_jobs = self._users_jobs

        if user_job.user:
            # Avoids a possible race condition: the job could be already in the list
            if user_job.id not in (j.id for j in users_jobs):
                users_jobs.appendleft(user_job)
        else:
            logger.warning('JobScheduler: try to start the job "%s", which is a'
                           ' system job -> command is ignored.', repr(user_job),
                          )

    def _start_job(self, job: Job):
        logger.info('JobScheduler: start %s', repr(job))

        self._procs[job.id] = python_subprocess(
            f'import django; '
            f'django.setup(); '
            f'from creme.creme_core.core.job import job_type_registry; '
            f'job_type_registry({job.id})'
        )

    def _end_job(self, job: Job):
        logger.info('JobScheduler: end %s', repr(job))
        proc = self._procs.pop(job.id, None)
        if proc is not None:
            proc.wait()  # TODO: use return code ??

    def _handle_kill(self, *args):
        logger.info('Job manager stops: %d running job(s)', len(self._procs))
        exit()

    def _handle_command_end(self, cmd: Command):
        job_id = cmd.data_id

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            logger.warning('JobScheduler.handle_command_end() -> invalid jod ID: %s', job_id)
        else:
            if job.user:
                self._running_userjob_ids.discard(job.id)
            else:
                if job.type.periodic == JobType.NOT_PERIODIC:
                    logger.critical('JobScheduler.handle_command_end() -> '
                                    'job "%s" is a system job and should be '
                                    '(pseudo-)periodic -> job is ignored.', repr(job),
                                    )
                else:
                    try:
                        reference_run = self._system_jobs_starts.pop(job.id)
                    except KeyError:
                        logger.warning('JobScheduler.handle_command_end() ->  try to end '
                                       'the job "%s" which was not started -> command is ignored', repr(job),
                                      )
                    else:
                        if job.enabled:  # Job may have been disabled during its execution
                            heappush(self._system_jobs, (self._next_wakeup(job, reference_run), job.id, job))

            self._end_job(job)

    def _handle_command_ping(self, cmd: Command) -> None:
        ping_uid = cmd.data_id
        logger.info('JobScheduler.handle_command_ping() -> PING id "%s"', ping_uid)
        self._queue.pong(ping_uid)

    def _handle_command_refresh(self, cmd: Command) -> None:
        job_id = cmd.data_id

        if job_id in self._system_jobs_starts:
            # If the job is running -> the new wake up is computed at the end of its execution ; so we ignore it.
            logger.info('JobScheduler.handle_command_refresh() -> try to REFRESH the job "%s",'
                        ' which is already running: command is useless.',
                        job_id,
                       )
            return

        system_jobs = self._system_jobs
        job = None

        # Retrieve/remove the job from the heap
        for i, (__, ___, old_job) in enumerate(system_jobs):
            if old_job.id == job_id:
                job = old_job
                del system_jobs[i]
                heapify(system_jobs)
                break
        else:
            logger.warning('JobScheduler.handle_command_refresh() -> invalid (system) jod ID: %s', job_id)
            return

        try:
            # NB: we do not use the result (which indicates a change, because pseudo-periodic jobs
            #     could need a new wakeup date without change in the job instance.
            job.update(cmd.data)
        except Exception as e:
            logger.warning('JobScheduler.handle_command_refresh() -> invalid refresh data: %s (%s)', cmd.data, e)
            return

        if not job.enabled:
            logger.warning('JobScheduler.handle_command_refresh() -> REFRESH job "%s": disabled', repr(job))
            return

        next_wakeup = self._next_wakeup(job)

        # XXX: this is an UGLY HACK. We have received a REFRESH command, but the
        #  data which should be used to compute the next wake up could be not
        #  available because of a transaction (ie: the command has been sent during
        #  this transaction) ; we force a wake up in a short time & pray that the
        #  migration is finished.
        #  TODO: improve this.
        #    => IDEA: create a transaction marker within the transaction, send
        #       its ID in the command, & wait for them to be reachable (so we
        #       are sure the transaction is finished).
        if job.enabled:
            secure_wakeup = now() + timedelta(seconds=30)
            next_wakeup = min(next_wakeup, secure_wakeup)

        heappush(system_jobs, (next_wakeup, job.id, job))
        logger.warning('JobScheduler.handle_command_refresh() -> REFRESH job "%s": next wake up at %s',
                       repr(job), date_format(localtime(next_wakeup), 'DATETIME_FORMAT'),
                      )

    def _handle_command_start(self, cmd: Command) -> None:
        job_id = cmd.data_id

        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            logger.warning('JobScheduler.handle_command_start() -> not yet existing jod ID: %s', job_id)
            def_job = self._DeferredJob(job_id=job_id)
            heappush(self._system_jobs, (def_job.next_wakeup(now()), job_id, def_job))
        else:
            self._push_user_job(job)

    def start(self, verbose: bool = True) -> None:
        logger.info('Job scheduler starts')

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
                for dt, __, job in system_jobs:
                    if not job.enabled:
                        print(f' - {job} (id={job.id}) -> disabled')
                    elif dt <= now_value:
                        print(f' - {job} (id={job.id}) -> run immediately')
                    else:
                        print(' - {job} (id={job_id}) -> next run at {start}'.format(
                                    job=job, job_id=job.id,
                                    start=date_format(localtime(dt), 'DATETIME_FORMAT'),
                                )
                             )
            else:
                print('No system job found.')

            if users_jobs:
                print('User jobs:')
                for job in users_jobs:
                    print(f' - {job} (id={job.id}; user={job.user})')
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
                    # job = heappop(system_jobs)[1]
                    job = heappop(system_jobs)[2]

                    if isinstance(job, self._DeferredJob):
                        try:
                            real_job = Job.objects.get(id=job.job_id)
                        except Job.DoesNotExist:
                            if job.reaches_trials_limit:
                                logger.warning('JobScheduler: deferred job does not exist after all'
                                               ' its trials (we forget it): %s', job.job_id,
                                              )
                            else:
                                heappush(system_jobs, (job.next_wakeup(now_value), job.job_id, job))
                                logger.warning('JobScheduler: deferred job still does not exist: %s', job.job_id)
                        else:
                            self._push_user_job(real_job)
                            logger.warning('JobScheduler: deferred job exists now: %s', real_job.id)
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
                logger.warning('JobScheduler: invalid command TYPE: %s', cmd_type)
