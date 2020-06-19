# -*- coding: utf-8 -*-

from datetime import timedelta

from django.test.utils import override_settings
from django.utils.timezone import now

from creme.creme_core.core.job import JobScheduler, _JobTypeRegistry
from creme.creme_core.core.reminder import Reminder, reminder_registry
from creme.creme_core.creme_jobs import reminder_type
from creme.creme_core.creme_jobs.base import JobType
from creme.creme_core.models import Job
from creme.creme_core.utils.date_period import HoursPeriod
from creme.creme_core.utils.dates import round_hour

from ..base import CremeTestCase


class JobTypeRegistryTestCase(CremeTestCase):
    def test_register01(self):
        "Not registered."
        class TestJobType(JobType):
            id = JobType.generate_id('creme_core', 'test')

        registry = _JobTypeRegistry()

        with self.assertLogs(level='CRITICAL') as logs_manager:
            job_type = registry.get(TestJobType.id)

        self.assertIsNone(job_type)
        self.assertEqual(
            logs_manager.output,
            [f'CRITICAL:creme.creme_core.core.job:Unknown JobType: {TestJobType.id}'],
        )

        job = Job.objects.create(type_id=TestJobType.id)

        with self.assertRaises(_JobTypeRegistry.Error):
            registry(job.id)

    def test_register02(self):
        "OK."
        class TestJobType(JobType):
            id = JobType.generate_id('creme_core', 'test')

        registry = _JobTypeRegistry()
        registry.register(TestJobType)

        self.assertEqual(TestJobType, registry.get(TestJobType.id))

        # TODO: override the job registry used in Job
        # job = Job.objects.create(type_id=TestJobType.id)
        # registry(job.id)
        # ...

    def test_register03(self):
        "Duplicated ID."
        class TestJobType1(JobType):
            id = JobType.generate_id('creme_core', 'test1')

        class TestJobType2(TestJobType1):
            # id = JobType.generate_id('creme_core', 'test2')
            pass

        registry = _JobTypeRegistry()
        registry.register(TestJobType1)

        with self.assertRaises(_JobTypeRegistry.Error) as cm:
            registry.register(TestJobType2)

        self.assertEqual(f'Duplicated job type id: {TestJobType1.id}',
                         str(cm.exception)
                        )

    def test_register04(self):
        "Empty ID."
        class TestJobType(JobType):
            # id = JobType.generate_id('creme_core', 'test')  NOPE
            pass

        registry = _JobTypeRegistry()

        with self.assertRaises(_JobTypeRegistry.Error) as cm:
            registry.register(TestJobType)

        self.assertEqual(f'Empty JobType id: {TestJobType}',
                         str(cm.exception)
                        )


class JobSchedulerTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        self.reminders = []

    def tearDown(self):
        super().tearDown()

        for reminder in self.reminders:
            reminder_registry.unregister(reminder)

    def _register_reminder(self, reminder):
        reminder_registry.register(reminder)
        self.reminders.append(reminder)

    @override_settings(PSEUDO_PERIOD=1)
    def test_next_wake_up01(self):
        "PSEUDO_PERIODIC job."
        rounded_hour = round_hour(now())
        job = Job.objects.get(type_id=reminder_type.id)

        if job.reference_run != rounded_hour:
            job.reference_run = rounded_hour
            job.save()

        self.assertEqual(HoursPeriod(value=1), job.real_periodicity)

        next_wakeup = JobScheduler()._next_wakeup

        next_hour = rounded_hour + timedelta(hours=1)
        self.assertEqual(next_hour, next_wakeup(job))

        job.reference_run = rounded_hour - timedelta(hours=1)  # should not be used because "rounded_hour" is given
        self.assertEqual(next_hour, next_wakeup(job, reference_run=rounded_hour))

    @override_settings(PSEUDO_PERIOD=1)
    def test_next_wake_up02(self):
        """PSEUDO_PERIODIC job + reminder return a wake up date before the new
        security period.
        """
        rounded_hour = round_hour(now())
        job = Job.objects.get(type_id=reminder_type.id)

        wake_up = rounded_hour + timedelta(minutes=20)

        class TestReminder(Reminder):
            id = Reminder.generate_id('creme_core', 'test_jobmanager_1')

            def next_wakeup(self, now_value):
                return wake_up

        self._register_reminder(TestReminder)
        self.assertEqual(wake_up, JobScheduler()._next_wakeup(job))

    @override_settings(PSEUDO_PERIOD=1)
    def test_next_wake_up03(self):
        """PSEUDO_PERIODIC job + reminder return a wake up date after the new
        security period.
        """
        rounded_hour = round_hour(now())
        job = Job.objects.get(type_id=reminder_type.id)

        class TestReminder(Reminder):
            id = Reminder.generate_id('creme_core', 'test_jobmanager_2')

            def next_wakeup(self, now_value):
                return rounded_hour + timedelta(minutes=70)

        self._register_reminder(TestReminder)

        self.assertEqual(rounded_hour + timedelta(hours=1),
                         JobScheduler()._next_wakeup(job)
                        )
