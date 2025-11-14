from django.utils.timezone import now

# Should be a test queue
from creme.creme_core.core.job import get_queue
from creme.creme_core.creme_jobs import reminder_type
from creme.creme_core.models import Job
from creme.creme_core.utils.date_period import MinutesPeriod
from creme.creme_core.utils.dates import dt_to_ISO8601

from ..base import CremeTestCase


class JobTestCase(CremeTestCase):
    def test_refresh01(self):
        "No refresh needed."
        queue = get_queue()
        queue.clear()

        job = self.get_object_or_fail(Job, type_id=reminder_type.id)
        self.assertIs(job.refresh(), False)
        self.assertListEqual([], queue.refreshed_jobs)

        # ---
        job.refresh(force=True)
        self.assertListEqual(
            [
                (
                    job,
                    {
                        'enabled':       job.enabled,
                        'reference_run': dt_to_ISO8601(job.reference_run),
                    },
                ),
            ],
            queue.refreshed_jobs,
        )

    def test_refresh02(self):
        "Enabled is changed."
        queue = get_queue()
        queue.clear()

        job = self.get_object_or_fail(Job, type_id=reminder_type.id)
        job.enabled = not job.enabled
        self.assertIs(job.refresh(), False)
        self.assertListEqual(
            [
                (
                    job,
                    {
                        'enabled':       job.enabled,
                        'reference_run': dt_to_ISO8601(job.reference_run),
                    },
                ),
            ],
            queue.refreshed_jobs,
        )

    def test_refresh03(self):
        "Reference_run is changed."
        queue = get_queue()
        queue.clear()

        job = self.get_object_or_fail(Job, type_id=reminder_type.id)
        job.reference_run = now()
        self.assertIs(job.refresh(), False)
        self.assertListEqual(
            [
                (
                    job,
                    {
                        'enabled':       job.enabled,
                        'reference_run': dt_to_ISO8601(job.reference_run),
                    },
                ),
            ],
            queue.refreshed_jobs,
        )

    def test_refresh04(self):
        "Periodicity is changed."
        queue = get_queue()
        queue.clear()

        job = self.get_object_or_fail(Job, type_id=reminder_type.id)
        job.periodicity = MinutesPeriod(1)
        self.assertIs(job.refresh(), False)
        self.assertEqual(
            [
                (
                    job,
                    {
                        'enabled':       job.enabled,
                        'reference_run': dt_to_ISO8601(job.reference_run),
                        'periodicity':   {'type': 'minutes', 'value': 1},
                    },
                ),
            ],
            queue.refreshed_jobs,
        )

    def test_update01(self):
        job = self.get_object_or_fail(Job, type_id=reminder_type.id)
        self.assertIs(False, job.update({}))

    def test_update02(self):
        "Enabled + change."
        job = self.get_object_or_fail(Job, type_id=reminder_type.id)

        new_enabled = not job.enabled
        self.assertIs(True, job.update({'enabled': new_enabled}))
        self.assertEqual(new_enabled, job.enabled)

    def test_update03(self):
        "Enabled + no change."
        job = self.get_object_or_fail(Job, type_id=reminder_type.id)

        new_enabled = job.enabled
        self.assertFalse(job.update({'enabled': new_enabled}))
        self.assertEqual(new_enabled, job.enabled)

    def test_update04(self):
        "Reference run + change."
        job = self.get_object_or_fail(Job, type_id=reminder_type.id)

        new_ref_run = '2017-12-25T14:00:00.000000Z'
        self.assertTrue(job.update({'reference_run': new_ref_run}))
        self.assertEqual(
            self.create_datetime(year=2017, month=12, day=25, hour=14, utc=True),
            job.reference_run,
        )

    def test_update05(self):
        "Reference run + no change."
        job = self.get_object_or_fail(Job, type_id=reminder_type.id)

        ref_run = job.reference_run
        self.assertFalse(job.update({'reference_run': dt_to_ISO8601(ref_run)}))
        self.assertEqual(ref_run, job.reference_run)

    def test_update06(self):
        "Periodicity + change."
        job = self.get_object_or_fail(Job, type_id=reminder_type.id)

        periodicity_dict = {'type': 'minutes', 'value': 3}
        self.assertTrue(job.update({'periodicity': periodicity_dict}))
        self.assertDictEqual(periodicity_dict, job.periodicity.as_dict())

    def test_update07(self):
        "Periodicity + no change."
        job = self.get_object_or_fail(Job, type_id=reminder_type.id)

        periodicity = job.periodicity = MinutesPeriod(1)
        self.assertFalse(job.update({'periodicity': periodicity.as_dict()}))
        self.assertEqual(periodicity, job.periodicity)

    def test_update08(self):
        "Several changes"
        job = self.get_object_or_fail(Job, type_id=reminder_type.id)

        new_enabled = not job.enabled
        new_ref_run = '2017-12-26T15:00:00.000000Z'
        self.assertTrue(job.update({
            'enabled':       new_enabled,
            'reference_run': new_ref_run,
        }))
        self.assertEqual(new_enabled, job.enabled)
        self.assertEqual(
            self.create_datetime(year=2017, month=12, day=26, hour=15, utc=True),
            job.reference_run,
        )

    # TODO: test sent data (beware to several changes)
    # TODO: test queue error + refresh
