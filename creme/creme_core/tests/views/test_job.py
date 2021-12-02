# -*- coding: utf-8 -*-

from collections import Counter

# from json import dumps as json_dump
from django.contrib.contenttypes.models import ContentType
from django.db.models import Max
from django.test.utils import override_settings
from django.urls import reverse
# from django.utils.encoding import smart_str
from django.utils.formats import date_format
from django.utils.timezone import localtime, now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.bricks import (
    EntityJobErrorsBrick,
    JobBrick,
    JobErrorsBrick,
    JobsBrick,
    MyJobsBrick,
)
# Should be a test queue
# from creme.creme_core.core.job import JobSchedulerQueue
from creme.creme_core.core.job import get_queue
from creme.creme_core.creme_jobs import (
    batch_process_type,
    reminder_type,
    temp_files_cleaner_type,
)
from creme.creme_core.creme_jobs.base import JobType
from creme.creme_core.models import EntityJobResult, Job
from creme.creme_core.utils.dates import dt_to_ISO8601

from ..fake_models import FakeOrganisation
from .base import BrickTestCaseMixin, ViewsTestCase


class JobViewsTestCase(ViewsTestCase, BrickTestCaseMixin):
    LIST_URL = reverse('creme_core__jobs')
    MINE_URL = reverse('creme_core__my_jobs')
    INFO_URL = reverse('creme_core__jobs_info')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # cls.queue = queue = JobSchedulerQueue.get_main_queue()
        cls.queue = queue = get_queue()
        cls._original_queue_ping = queue.ping

        cls.ct_orga_id = ContentType.objects.get_for_model(FakeOrganisation).id

    def tearDown(self):
        self.queue.ping = self._original_queue_ping

    # def _assertCount(self, response, found, count):
    #     self.assertEqual(count, smart_str(response.content).count(found))

    @staticmethod
    def _build_enable_url(job):
        return reverse('creme_core__enable_job', args=(job.id,))

    @staticmethod
    def _build_delete_url(job):
        return reverse('creme_core__delete_job', args=(job.id,))

    @staticmethod
    def _build_disable_url(job):
        return reverse('creme_core__disable_job', args=(job.id,))

    def _create_batchprocess_job(self, user=None, status=Job.STATUS_WAIT):
        return Job.objects.create(
            user=user or self.user,
            type_id=batch_process_type.id,
            language='en',
            status=status,
            # raw_data=json_dump({
            #     'ctype': self.ct_orga_id,
            #     'actions': [],
            # }),
            data={
                'ctype': self.ct_orga_id,
                'actions': [],
            },
        )

    def _create_invalid_job(self, user=None, status=Job.STATUS_WAIT):
        return Job.objects.create(
            user=user or self.user,
            type_id=JobType.generate_id('creme_core', 'invalid'),
            language='en',
            status=status,
            # raw_data='[]',
            data=[],
        )

    def test_detailview01(self):
        self.login()

        job = self._create_batchprocess_job()
        url = job.get_absolute_url()
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/job/detail.html')

        with self.assertNoException():
            context = response1.context
            cxt_job = context['job']
            cxt_url = context['list_url']
            context['results_bricks']  # NOQA
            context['bricks_reload_url']  # NOQA

        self.assertEqual(job, cxt_job)
        self.assertEqual(self.MINE_URL, cxt_url)

        tree1 = self.get_html_tree(response1.content)
        info_brick_node1 = self.get_brick_node(tree1, JobBrick.id_)
        info_buttons1 = self.get_brick_header_buttons(info_brick_node1)
        self.assertBrickHeaderHasNoButton(info_buttons1, job.get_edit_absolute_url())
        self.assertBrickHeaderHasNoButton(info_buttons1, job.get_delete_absolute_url())
        self.assertBrickHeaderHasNoButton(
            info_buttons1, reverse('creme_core__disable_job', args=(job.id,)),
        )
        self.assertBrickHeaderHasNoButton(
            info_buttons1, reverse('creme_core__enable_job', args=(job.id,)),
        )

        self.get_brick_node(tree1, EntityJobErrorsBrick.id_)

        # ---
        job.status = Job.STATUS_OK
        job.save()

        response2 = self.assertGET200(url)
        info_brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content), JobBrick.id_,
        )
        info_buttons2 = self.get_brick_header_buttons(info_brick_node2)
        # TODO: test back URL (assertBrickHeaderHasButton => get_button_or_fail())
        self.assertBrickHeaderHasButton(
            info_buttons2,
            url=job.get_delete_absolute_url(), label=_('Delete the job'),
        )

    def test_detailview02(self):
        "List URL."
        self.login()

        job = self._create_batchprocess_job()
        response = self.assertGET200(
            job.get_absolute_url(), data={'list_url': self.LIST_URL},
        )

        with self.assertNoException():
            cxt_url = response.context['list_url']

        self.assertEqual(self.LIST_URL, cxt_url)

        # Invalid URL
        response = self.assertGET200(
            job.get_absolute_url(), data={'list_url': 'http://insecure.com'},
        )
        self.assertEqual(self.MINE_URL, response.context.get('list_url'))

    def test_detailview03(self):
        "Credentials."
        self.login(is_superuser=False)

        job1 = self._create_batchprocess_job()
        self.assertGET200(job1.get_absolute_url())

        job2 = self._create_batchprocess_job(user=self.other_user)
        self.assertGET403(job2.get_absolute_url())

    def test_detailview04(self):
        "Invalid type."
        self.login()

        job = self._create_invalid_job()
        self.assertIsNone(job.type)
        self.assertIsNone(job.get_config_form_class())
        self.assertGET404(job.get_absolute_url())
        self.assertListEqual([], job.stats)

    def test_detailview05(self):
        "System job."
        self.login()

        job = self.get_object_or_fail(Job, type_id=temp_files_cleaner_type.id)
        url = job.get_absolute_url()
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/job/detail.html')

        tree1 = self.get_html_tree(response1.content)
        info_brick_node1 = self.get_brick_node(tree1, JobBrick.id_)
        info_buttons1 = self.get_brick_header_buttons(info_brick_node1)
        self.assertBrickHeaderHasButton(
            info_buttons1,
            url=job.get_edit_absolute_url(), label=_("Edit the job's configuration"),
        )
        self.assertBrickHeaderHasNoButton(info_buttons1, job.get_delete_absolute_url())
        self.assertBrickHeaderHasButton(
            info_buttons1,
            url=reverse('creme_core__disable_job', args=(job.id,)),
            label=_('Disable'),
        )
        self.assertBrickHeaderHasNoButton(
            info_buttons1, reverse('creme_core__enable_job', args=(job.id,)),
        )

        self.get_brick_node(tree1, JobErrorsBrick.id_)

        # -----
        job.enabled = False
        job.save()

        response2 = self.assertGET200(url)
        info_brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content), JobBrick.id_,
        )
        info_buttons2 = self.get_brick_header_buttons(info_brick_node2)
        self.assertBrickHeaderHasButton(
            info_buttons2,
            url=reverse('creme_core__enable_job', args=(job.id,)),
            label=_('Enable'),
        )
        self.assertBrickHeaderHasNoButton(
            info_buttons2, reverse('creme_core__disable_job', args=(job.id,)),
        )

    def test_editview01(self):
        "Not periodic."
        self.login()

        job = self._create_batchprocess_job()
        self.assertEqual(JobType.NOT_PERIODIC, job.type.periodic)
        self.assertIsNone(job.periodicity)
        self.assertIsNone(job.real_periodicity)
        self.assertRaises(ValueError, job.type.next_wakeup, job, now())

        self.assertGET409(job.get_edit_absolute_url())

    @override_settings(PSEUDO_PERIOD=2)
    def test_editview02(self):
        "Pseudo periodic"
        self.login()

        job = self.get_object_or_fail(Job, type_id=reminder_type.id)
        self.assertEqual(JobType.PSEUDO_PERIODIC, job.type.periodic)
        self.assertIsNone(job.user)
        self.assertIsNone(job.periodicity)
        self.assertDictEqual(
            {'type': 'hours', 'value': 2}, job.real_periodicity.as_dict(),
        )

        # Tests of "next_wakeup()" are deeper in the 'assistants' app
        with self.assertNoException():
            job.type.next_wakeup(job, now())

        self.assertGET409(job.get_edit_absolute_url())

    def test_editview03(self):
        "Periodic: edit periodicity + specific data."
        # queue = JobSchedulerQueue.get_main_queue()
        queue = self.queue
        queue.clear()

        self.login()
        self.assertListEqual([], queue.refreshed_jobs)

        job = self.get_object_or_fail(Job, type_id=temp_files_cleaner_type.id)
        self.assertEqual(JobType.PERIODIC, job.type.periodic)
        self.assertIsNone(job.user)

        old_reference_run = job.reference_run

        pdict = {'type': 'days', 'value': 1}
        self.assertDictEqual(pdict, job.periodicity.as_dict())
        self.assertDictEqual(pdict, job.real_periodicity.as_dict())

        with self.assertNoException():
            jdata = job.data

        self.assertEqual({'delay': {'type': 'days', 'value': 1}}, jdata)

        url = job.get_edit_absolute_url()
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(
            _('Edit the job «{object}»').format(object=job.type),
            context.get('title'),
        )
        self.assertEqual(
            _('Save the modifications'), context.get('submit_label'),
        )

        # ---
        response = self.client.post(
            url,
            data={
                'reference_run': date_format(
                    localtime(job.reference_run), 'DATETIME_FORMAT',
                ),
                'periodicity_0': 'minutes',
                'periodicity_1': '180',

                'delay_0': 'weeks',
                'delay_1': '2',
            },
        )
        self.assertNoFormError(response)

        job = self.refresh(job)
        periodicity_dict = {'type': 'minutes', 'value': 180}
        self.assertEqual(periodicity_dict, job.periodicity.as_dict())
        self.assertEqual(old_reference_run, job.reference_run)
        self.assertEqual({'delay': {'type': 'weeks', 'value': 2}}, job.data)
        self.assertListEqual(
            [
                (
                    job,
                    {
                        'enabled':       True,
                        'reference_run': dt_to_ISO8601(job.reference_run),
                        'periodicity':   periodicity_dict,
                    },
                ),
            ],
            queue.refreshed_jobs
        )

    def test_editview04(self):
        "Periodic: edit reference_run."
        # queue = JobSchedulerQueue.get_main_queue()
        queue = self.queue
        queue.clear()

        self.login()
        self.assertListEqual([], queue.refreshed_jobs)

        job = self.get_object_or_fail(Job, type_id=temp_files_cleaner_type.id)

        pdict = {'type': 'days', 'value': 1}
        self.assertEqual(pdict, job.periodicity.as_dict())

        response = self.client.post(
            job.get_edit_absolute_url(),
            data={
                'reference_run': '26-08-2014 14:00:00',
                'periodicity_0': pdict['type'],
                'periodicity_1': str(pdict['value']),

                'delay_0': 'days',
                'delay_1': 2,
            },
        )
        self.assertNoFormError(response)

        job = self.refresh(job)
        self.assertEqual(pdict, job.periodicity.as_dict())
        self.assertEqual(
            self.create_datetime(year=2014, month=8, day=26, hour=14),
            job.reference_run,
        )
        self.assertDictEqual({'delay': {'type': 'days', 'value': 2}}, job.data)

        self.assertTrue(queue.refreshed_jobs)

    def test_editview05(self):
        "No change of periodicity/reference_run."
        # queue = JobSchedulerQueue.get_main_queue()
        queue = self.queue
        queue.clear()

        self.login()

        job = self.get_object_or_fail(Job, type_id=temp_files_cleaner_type.id)
        old_reference_run = job.reference_run

        pdict = {'type': 'days', 'value': 1}
        self.assertDictEqual(pdict, job.periodicity.as_dict())

        response = self.client.post(
            job.get_edit_absolute_url(),
            data={
                'reference_run': date_format(
                    localtime(job.reference_run),
                    'DATETIME_FORMAT',
                ),
                'periodicity_0': pdict['type'],
                'periodicity_1': str(pdict['value']),

                'delay_0': 'weeks',
                'delay_1': 1,
            },
        )
        self.assertNoFormError(response)

        job = self.refresh(job)
        self.assertEqual(pdict, job.periodicity.as_dict())
        self.assertEqual(old_reference_run, job.reference_run)
        self.assertDictEqual({'delay': {'type': 'weeks', 'value': 1}}, job.data)

        self.assertListEqual([], queue.refreshed_jobs)

    def test_editview06(self):
        "Periodic: credentials errors."
        self.login(is_superuser=False)

        job = self.get_object_or_fail(Job, type_id=temp_files_cleaner_type.id)
        self.assertGET403(job.get_edit_absolute_url())

    def test_jobs_all01(self):
        self.login()
        job_count = 2
        for i in range(job_count):
            self._create_batchprocess_job()

        response = self.assertGET200(self.LIST_URL)
        self.assertTemplateUsed(response, 'creme_core/job/list-all.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        # self._assertCount(response, str(batch_process_type.verbose_name), job_count)
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), JobsBrick.id_
        )
        counter = Counter(
            n.text for n in brick_node.findall('.//td[@class="job-type"]')
        )
        self.assertEqual(1, counter[_('Temporary files cleaner')])
        self.assertEqual(1, counter[_('Reminders')])
        self.assertEqual(2, counter[str(batch_process_type.verbose_name)])

    def test_jobs_all02(self):
        "Not super-user: forbidden."
        self.login(is_superuser=False)
        self.assertGET403(self.LIST_URL)

    @override_settings(MAX_JOBS_PER_USER=1)
    def test_jobs_all03(self):
        "Max job message"
        self.login()

        # Not counted in max
        self._create_batchprocess_job(status=Job.STATUS_OK)  # Finished
        Job.objects.create(type_id=batch_process_type.id)  # No user

        response = self.assertGET200(self.LIST_URL)
        self.assertTemplateUsed(response, 'creme_core/job/list-all.html')

        msg = _('You must wait that your job is finished in order to create a new one.')
        self.assertNotContains(response, msg)

        self._create_batchprocess_job(status=Job.STATUS_WAIT)

        response = self.assertGET200(self.LIST_URL)
        self.assertTemplateUsed(response, 'creme_core/job/list-all.html')
        self.assertContains(response, msg)

    @override_settings(MAX_JOBS_PER_USER=2)
    def test_jobs_all04(self):
        "Max job message (several messages)"
        self.login()

        for i in range(2):
            self._create_batchprocess_job(status=Job.STATUS_WAIT)

        response = self.assertGET200(self.LIST_URL)
        self.assertContains(
            response,
            _(
                'You must wait that one of your jobs is finished in order to '
                'create a new one.'
            ),
        )

    def test_jobs_all05(self):
        "Invalid type."
        self.login()
        self._create_invalid_job()
        self.assertGET200(self.LIST_URL)

    def test_my_jobs01(self):
        self.login()

        job_count = 2
        for i in range(job_count):
            self._create_batchprocess_job()

        response = self.assertGET200(self.MINE_URL)
        self.assertTemplateUsed(response, 'creme_core/job/list-mine.html')
        self.assertEqual(
            reverse('creme_core__reload_bricks'),
            response.context.get('bricks_reload_url'),
        )

        tree = self.get_html_tree(response.content)
        brick_node = self.get_brick_node(tree, MyJobsBrick.id_)
        self.assertListEqual(
            [str(_('Core'))] * job_count,
            [n.text for n in brick_node.findall('.//td[@class="job-app"]')],
        )
        self.assertListEqual(
            [str(batch_process_type.verbose_name)] * job_count,
            [n.text for n in brick_node.findall('.//td[@class="job-type"]')],
        )
        # TODO: complete

    def test_my_jobs02(self):
        "Credentials."
        self.login(is_superuser=False)
        self._create_batchprocess_job()
        response1 = self.assertGET200(self.MINE_URL)
        # self._assertCount(response1, str(batch_process_type.verbose_name), 1)
        brick_node1 = self.get_brick_node(
            self.get_html_tree(response1.content), MyJobsBrick.id_
        )
        job_vname = str(batch_process_type.verbose_name)
        self.assertListEqual(
            [job_vname],
            [n.text for n in brick_node1.findall('.//td[@class="job-type"]')],
        )

        self._create_batchprocess_job(user=self.other_user)
        response2 = self.assertGET200(self.MINE_URL)
        # self._assertCount(response2, str(batch_process_type.verbose_name), 1)  # Only job1
        brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content), MyJobsBrick.id_
        )
        self.assertListEqual(
            [job_vname],  # Only job1
            [n.text for n in brick_node2.findall('.//td[@class="job-type"]')],
        )

    @override_settings(MAX_JOBS_PER_USER=1)
    def test_my_jobs03(self):
        "Max job message."
        self.login()

        # Not counted in max
        self._create_batchprocess_job(status=Job.STATUS_ERROR)  # Finished
        Job.objects.create(type_id=batch_process_type.id, status=Job.STATUS_OK)  # No user

        response = self.assertGET200(self.MINE_URL)
        self.assertTemplateUsed(response, 'creme_core/job/list-mine.html')

        msg = _('You must wait that your job is finished in order to create a new one.')
        self.assertNotContains(response, msg)

        self._create_batchprocess_job(status=Job.STATUS_WAIT)

        response = self.assertGET200(self.MINE_URL)
        self.assertTemplateUsed(response, 'creme_core/job/list-mine.html')
        self.assertContains(response, msg)

    @override_settings(MAX_JOBS_PER_USER=2)
    def test_my_jobs04(self):
        "Max job message (several messages)."
        self.login()

        for i in range(2):
            self._create_batchprocess_job(status=Job.STATUS_WAIT)

        response = self.assertGET200(self.MINE_URL)
        self.assertContains(
            response,
            _('You must wait that one of your jobs is finished in order to create a new one.')
        )

    def test_my_jobs05(self):
        "Invalid type."
        self.login()
        self._create_invalid_job()
        self.assertGET200(self.MINE_URL)

    def test_clear01(self):
        user = self.login()
        job = self._create_batchprocess_job(status=Job.STATUS_OK)

        orga = FakeOrganisation.objects.create(user=user)
        jresult = EntityJobResult.objects.create(job=job, entity=orga)

        del_url = self._build_delete_url(job)
        self.assertGET405(del_url)

        response = self.assertPOST200(del_url, follow=True)
        self.assertDoesNotExist(job)
        self.assertDoesNotExist(jresult)
        self.assertRedirects(response, self.MINE_URL)

    def test_clear02(self):
        "Redirection."
        user = self.login()
        job = self._create_batchprocess_job(status=Job.STATUS_OK)

        orga = FakeOrganisation.objects.create(user=user)
        jresult = EntityJobResult.objects.create(job=job, entity=orga)

        response = self.assertPOST200(
            self._build_delete_url(job),
            data={'back_url': self.LIST_URL}, follow=True,
        )
        self.assertDoesNotExist(job)
        self.assertDoesNotExist(jresult)
        self.assertRedirects(response, self.LIST_URL)

    def test_clear03(self):
        "status = Job.STATUS_ERROR + AJAX."
        self.login()
        job = self._create_batchprocess_job(status=Job.STATUS_ERROR)

        self.assertPOST200(
            self._build_delete_url(job), HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertDoesNotExist(job)

    def test_clear04(self):
        "Can only clear finished jobs."
        self.login()
        job = self._create_batchprocess_job()
        self.assertPOST409(self._build_delete_url(job), follow=True)

    def test_clear05(self):
        "Credentials."
        self.login(is_superuser=False)

        job = self._create_batchprocess_job(
            user=self.other_user, status=Job.STATUS_OK,
        )
        self.assertPOST403(self._build_delete_url(job), follow=True)

        job = self._create_batchprocess_job(status=Job.STATUS_OK)
        self.assertPOST200(self._build_delete_url(job), follow=True)

    def test_clear06(self):
        "Can not clear a system job."
        self.login()

        # No user -> system job
        job = Job.objects.create(
            type_id=batch_process_type.id, status=Job.STATUS_OK,
        )
        self.assertPOST409(self._build_delete_url(job), follow=True)

    def test_disable01(self):
        # queue = JobSchedulerQueue.get_main_queue()
        queue = self.queue
        queue.clear()

        self.login()
        self.assertEqual([], queue.refreshed_jobs)

        job = Job.objects.create(type_id=batch_process_type.id)  # No user -> system job
        self.assertIs(job.enabled, True)
        self.assertListEqual([], queue.refreshed_jobs)

        disable_url = self._build_disable_url(job)
        self.assertGET405(disable_url)

        self.assertPOST200(disable_url)
        self.assertIs(self.refresh(job).enabled, False)
        self.assertListEqual(
            [(
                job,
                {
                    'enabled':       False,
                    'reference_run': dt_to_ISO8601(job.reference_run),
                },
            )],
            queue.refreshed_jobs,
        )

        enable_url = self._build_enable_url(job)
        self.assertGET405(enable_url)

        queue.clear()
        self.assertPOST200(enable_url)
        self.assertIs(self.refresh(job).enabled, True)
        self.assertListEqual(
            [(
                job,
                {
                    'enabled':       True,
                    'reference_run': dt_to_ISO8601(job.reference_run),
                },
            )],
            queue.refreshed_jobs,
        )

    def test_disable02(self):
        "Cannot disable a non-system job."
        self.login()

        job = self._create_batchprocess_job()
        self.assertPOST409(self._build_disable_url(job))

    def test_disable03(self):
        "Only super-users can edit a system job"
        self.login(is_superuser=False)

        job = Job.objects.create(type_id=batch_process_type.id)
        self.assertPOST403(self._build_disable_url(job))

    def test_status01(self):
        self.login(is_superuser=False)
        url = self.INFO_URL

        job = self._create_batchprocess_job()
        response = self.assertGET200(url, data={'id': [job.id]})
        self.assertEqual('application/json', response['Content-Type'])
        self.assertDictEqual(
            {
                str(job.id): {
                    'status': Job.STATUS_WAIT,
                    'ack_errors': 0,
                    'progress': {
                        'label': ngettext(
                            '{count} entity has been processed.',
                            '{count} entities have been processed.',
                            0
                        ).format(count=0),
                        'percentage': None,
                    },
                }
            },
            response.json(),
        )

        job = self._create_batchprocess_job(status=Job.STATUS_OK)
        response = self.assertGET200(url, data={'id': [job.id]})
        self.assertDictEqual(
            {
                str(job.id): {
                    'status': Job.STATUS_OK,
                    'ack_errors': 0,
                    'progress': {
                        'label': ngettext(
                            '{count} entity has been processed.',
                            '{count} entities have been processed.',
                            0
                        ).format(count=0),
                        'percentage': None,
                    },
                }
            },
            response.json(),
        )

        job = self._create_batchprocess_job(user=self.other_user)
        response = self.assertGET200(url, data={'id': [job.id]})
        self.assertDictEqual({str(job.id): 'Job is not allowed'}, response.json())

        invalid_id = Job.objects.aggregate(Max('id'))['id__max'] + 1
        response = self.assertGET200(url, data={'id': [invalid_id]})
        self.assertDictEqual({str(invalid_id): 'Invalid job ID'}, response.json())

        invalid_id = 'invalid'
        response = self.assertGET200(url, data={'id': [invalid_id]})
        self.assertDictEqual({}, response.json())

    def test_status02(self):
        "Several jobs"
        self.login(is_superuser=False)

        job1 = self._create_batchprocess_job()
        job2 = self._create_batchprocess_job(status=Job.STATUS_OK)
        job3 = self._create_batchprocess_job(user=self.other_user)
        response = self.assertGET200(
            self.INFO_URL, data={'id': [job1.id, job3.id, job2.id]},
        )

        content = response.json()
        self.assertEqual(3, len(content))

        label = ngettext(
            '{count} entity has been processed.',
            '{count} entities have been processed.',
            0
        ).format(count=0)
        self.assertDictEqual(
            {
                'status': Job.STATUS_WAIT,
                'ack_errors': 0,
                'progress': {
                    'label': label,
                    'percentage': None,
                },
            },
            content[str(job1.id)],
        )
        self.assertDictEqual(
            {
                'status': Job.STATUS_OK,
                'ack_errors': 0,
                'progress': {
                    'label': label,
                    'percentage': None,
                },
            },
            content[str(job2.id)],
        )
        self.assertEqual('Job is not allowed', content[str(job3.id)])

    def test_status03(self):
        "Queue error."
        error = 'Arggggg'
        self.queue.ping = lambda: error

        self.login(is_superuser=False)

        response = self.assertGET200(self.INFO_URL)
        self.assertEqual({'error': error}, response.json())

    def test_status04(self):
        "ACK error"
        self.queue.start_job = lambda job: True
        self.login(is_superuser=False)

        job = self._create_batchprocess_job()
        self.assertEqual(1, self.refresh(job).ack_errors)

        response = self.assertGET200(self.INFO_URL, data={'id': [job.id]})
        self.assertDictEqual(
            {
                str(job.id): {
                    'status': Job.STATUS_WAIT,
                    'ack_errors': 1,
                    'progress': {
                        'label': ngettext(
                            '{count} entity has been processed.',
                            '{count} entities have been processed.',
                            0
                        ).format(count=0),
                        'percentage': None,
                    },
                },
            },
            response.json(),
        )

    def _aux_test_reload(self, job, brick_id):
        response = self.assertGET200(
            reverse('creme_core__reload_job_bricks', args=(job.id,)),
            data={'brick_id': brick_id},
        )

        results = response.json()
        self.assertIsList(results, length=1)

        result = results[0]
        self.assertIsList(result, length=2)
        self.assertEqual(brick_id, result[0])

        doc = self.get_html_tree(result[1])
        self.get_brick_node(doc, brick_id)

    def test_reload01(self):
        self.login()
        job = self.get_object_or_fail(Job, type_id=reminder_type.id)

        self._aux_test_reload(job, JobBrick.id_)
        self._aux_test_reload(job, JobErrorsBrick.id_)

    def test_reload02(self):
        self.login()
        job = self._create_batchprocess_job()

        self._aux_test_reload(job, JobBrick.id_)
        self._aux_test_reload(job, EntityJobErrorsBrick.id_)

    def test_reload03(self):
        self.login(is_superuser=False)
        job = self._create_batchprocess_job(user=self.other_user)
        self.assertGET403(
            reverse('creme_core__reload_job_bricks', args=(job.id,)),
            data={'brick_id': JobBrick.id_},
        )
