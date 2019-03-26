# -*- coding: utf-8 -*-

try:
    from datetime import timedelta

    from django.test.utils import override_settings
    from django.utils.timezone import now

    from ..base import CremeTestCase

    from creme.creme_core.core.job import JobManager
    from creme.creme_core.core.reminder import Reminder, reminder_registry
    from creme.creme_core.creme_jobs import reminder_type
    from creme.creme_core.models import Job
    from creme.creme_core.utils.date_period import HoursPeriod
    from creme.creme_core.utils.dates import round_hour
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class JobManagerTestCase(CremeTestCase):
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

        next_wakeup = JobManager()._next_wakeup

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
        self.assertEqual(wake_up, JobManager()._next_wakeup(job))

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
                         JobManager()._next_wakeup(job)
                        )
