# -*- coding: utf-8 -*-

try:
    from json import loads as json_load

    from django.apps import apps
    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.db.models import Max
    from django.test.utils import override_settings
    from django.utils.encoding import smart_unicode
    from django.utils.formats import date_format
    from django.utils.timezone import localtime, now
    from django.utils.translation import ugettext as _

    from ..base import skipIfNotInstalled
    from .base import ViewsTestCase
    from creme.creme_core.blocks import job_block, job_errors_block, entity_job_errors_block
    from creme.creme_core.core.job import JobManagerQueue  # Should be a test queue
    from creme.creme_core.creme_jobs import batch_process_type, reminder_type
    from creme.creme_core.creme_jobs.base import JobType
    from creme.creme_core.models import Job, JobResult, EntityJobResult
    from creme.creme_core.core.job import JobManagerQueue  # Should be a test queue

    from ..fake_models import FakeOrganisation as Organisation

    if apps.is_installed('creme.crudity'):
        from creme.crudity.creme_jobs import crudity_synchronize_type
    #     crudity_installed = True
    # else:
    #     crudity_installed = False
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class JobViewsTestCase(ViewsTestCase):
    LIST_URL = '/creme_core/job/all'
    INFO_URL = '/creme_core/job/info'

    @classmethod
    def setUpClass(cls):
        # ViewsTestCase.setUpClass()
        super(JobViewsTestCase, cls).setUpClass()
        # Job.objects.all().delete()

        # apps = ['creme_core', 'creme_config']
        #
        # if crudity_installed:
        #     apps.append('crudity')
        #
        # cls.populate(*apps)

        cls.queue = queue = JobManagerQueue.get_main_queue()
        cls._original_queue_ping = queue.ping

    def tearDown(self):
        self.queue.ping = self._original_queue_ping

    # TODO: move to base class ?
    def _assertCount(self, response, found, count):
        self.assertEqual(count, smart_unicode(response.content).count(found))

    def _build_enable_url(self, job):
        return '/creme_core/job/%s/enable' % job.id

    def _build_delete_url(self, job):
        return '/creme_core/job/%s/delete' % job.id

    def _build_disable_url(self, job):
        return '/creme_core/job/%s/disable' % job.id

    def _create_batchprocess_job(self, user=None, status=Job.STATUS_WAIT):
        if user is None:
            user = self.user

        return Job.objects.create(user=user,
                                  type_id=batch_process_type.id,
                                  language='en',
                                  status=status,
                                  raw_data='{"ctype": %s, "actions": []}' % ContentType.objects.get_for_model(Organisation).id,
                                 )

    def test_detailview01(self):
        self.login()

        job = self._create_batchprocess_job()
        response = self.assertGET200(job.get_absolute_url())
        self.assertTemplateUsed(response, 'creme_core/job.html')

        with self.assertNoException():
            cxt_job = response.context['job']

        self.assertEqual(job, cxt_job)

        self.assertContains(response, ' id="%s"' % entity_job_errors_block.id_)

    def test_detailview02(self):
        "Credentials"
        self.login(is_superuser=False)

        job = self._create_batchprocess_job()
        self.assertGET200(job.get_absolute_url())

        job = self._create_batchprocess_job(user=self.other_user)
        self.assertGET403(job.get_absolute_url())

    def test_editview01(self):
        "Not periodic"
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
        self.assertEqual({'type': 'hours', 'value': 2},
                         job.real_periodicity.as_dict()
                        )

        # Tests of "next_wakeup()" are deeper in the 'assistants' app
        with self.assertNoException():
            job.type.next_wakeup(job, now())

        self.assertGET409(job.get_edit_absolute_url())

    @skipIfNotInstalled('creme.crudity')
    def test_editview03(self):
        "Periodic: edit periodicity"
        queue = JobManagerQueue.get_main_queue()
        queue.clear()

        self.login()
        self.assertEqual([], queue.refreshed_jobs)

        job = self.get_object_or_fail(Job, type_id=crudity_synchronize_type.id)
        self.assertEqual(JobType.PERIODIC, job.type.periodic)
        self.assertIsNone(job.user)

        old_reference_run = job.reference_run

        pdict = {'type': 'minutes', 'value': 30}
        self.assertEqual(pdict, job.periodicity.as_dict())
        self.assertEqual(pdict, job.real_periodicity.as_dict())

        url = job.get_edit_absolute_url()
        self.assertGET200(url)

        response = self.client.post(url, data={'reference_run': date_format(localtime(job.reference_run),
                                                                            'DATETIME_FORMAT',
                                                                           ),
                                               'periodicity_0': 'minutes',
                                               'periodicity_1': '180',

                                               'user': self.user.id,
                                              },
                                   )
        self.assertNoFormError(response)

        job = self.refresh(job)
        self.assertEqual({'type': 'minutes', 'value': 180}, job.periodicity.as_dict())
        self.assertEqual(old_reference_run, job.reference_run)

        self.assertEqual([job], queue.refreshed_jobs)

    @skipIfNotInstalled('creme.crudity')
    def test_editview04(self):
        "Periodic: edit reference_run"
        queue = JobManagerQueue.get_main_queue()
        queue.clear()

        self.login()
        self.assertEqual([], queue.refreshed_jobs)

        job = self.get_object_or_fail(Job, type_id=crudity_synchronize_type.id)

        pdict = {'type': 'minutes', 'value': 30}
        self.assertEqual(pdict, job.periodicity.as_dict())

        response = self.client.post(job.get_edit_absolute_url(),
                                    data={'reference_run': '26-08-2014 14:00:00',
                                          'periodicity_0': pdict['type'],
                                          'periodicity_1': str(pdict['value']),

                                          'user': self.user.id,
                                         },
                                   )
        self.assertNoFormError(response)

        job = self.refresh(job)
        self.assertEqual(pdict, job.periodicity.as_dict())
        self.assertEqual(self.create_datetime(year=2014, month=8, day=26, hour=14),
                         job.reference_run
                        )

        self.assertEqual([job], queue.refreshed_jobs)

    @skipIfNotInstalled('creme.crudity')
    def test_editview05(self):
        "No change"
        queue = JobManagerQueue.get_main_queue()
        queue.clear()

        self.login()

        job = self.get_object_or_fail(Job, type_id=crudity_synchronize_type.id)
        old_reference_run = job.reference_run

        pdict = {'type': 'minutes', 'value': 30}
        self.assertEqual(pdict, job.periodicity.as_dict())

        response = self.client.post(job.get_edit_absolute_url(),
                                    data={'reference_run': date_format(localtime(job.reference_run),
                                                                       'DATETIME_FORMAT',
                                                                      ),
                                          'periodicity_0': pdict['type'],
                                          'periodicity_1': str(pdict['value']),

                                          'user': self.user.id,
                                         },
                                   )
        self.assertNoFormError(response)

        job = self.refresh(job)
        self.assertEqual(pdict, job.periodicity.as_dict())
        self.assertEqual(old_reference_run, job.reference_run)

        self.assertEqual([], queue.refreshed_jobs)

    @skipIfNotInstalled('creme.crudity')
    def test_editview06(self):
        "Periodic: credentials errors"
        self.login(is_superuser=False)

        job = self.get_object_or_fail(Job, type_id=crudity_synchronize_type.id)
        self.assertGET403(job.get_edit_absolute_url())

    def test_listview01(self):
        self.login()
        job_count = 2
        for i in xrange(job_count):
            self._create_batchprocess_job()

        response = self.assertGET200(self.LIST_URL)
        self.assertTemplateUsed('creme_core/jobs.html')

        self._assertCount(response, unicode(batch_process_type.verbose_name), job_count)

    def test_listview02(self):
        "Credentials"
        self.login(is_superuser=False)
        job1 = self._create_batchprocess_job()
        response = self.assertGET200(self.LIST_URL)
        self._assertCount(response, unicode(batch_process_type.verbose_name), 1)

        job2 = self._create_batchprocess_job(user=self.other_user)
        response = self.assertGET200(self.LIST_URL)
        self._assertCount(response, unicode(batch_process_type.verbose_name), 1)  # Only job1

    @override_settings(MAX_JOBS_PER_USER=1)
    def test_listview03(self):
        "Max job message"
        self.login()

        Job.objects.create(type_id=batch_process_type.id)  # No user -> not counted in max

        response = self.assertGET200(self.LIST_URL)
        self.assertTemplateUsed('creme_core/jobs.html')

        msg = _('You must delete your job in order to create a new one.')
        self.assertNotContains(response, msg)

        self._create_batchprocess_job()

        response = self.assertGET200(self.LIST_URL)
        self.assertTemplateUsed('creme_core/jobs.html')
        self.assertContains(response, msg)

    @override_settings(MAX_JOBS_PER_USER=2)
    def test_listview04(self):
        "Max job message (several messages)"
        self.login()

        for i in xrange(2):
            self._create_batchprocess_job()

        response = self.assertGET200(self.LIST_URL)
        self.assertContains(response,
                            _('You must delete one of your jobs in order to create a new one.')
                           )

    def test_clear01(self):
        self.login()
        job = self._create_batchprocess_job(status=Job.STATUS_OK)

        orga = Organisation.objects.create(user=self.user)
        jresult = EntityJobResult.objects.create(job=job, entity=orga)

        del_url = self._build_delete_url(job)
        self.assertGET404(del_url)

        response = self.assertPOST200(del_url, follow=True)
        self.assertDoesNotExist(job)
        self.assertDoesNotExist(jresult)
        self.assertRedirects(response, '/creme_core/job/all')

    def test_clear02(self):
        "status = Job.STATUS_ERROR + ajax"
        self.login()
        job = self._create_batchprocess_job(status=Job.STATUS_ERROR)
        orga = Organisation.objects.create(user=self.user)
        self.assertPOST200(self._build_delete_url(job),
                           HTTP_X_REQUESTED_WITH='XMLHttpRequest',
                          )
        self.assertDoesNotExist(job)

    def test_clear03(self):
        "Can only clear finished jobs"
        self.login()
        job = self._create_batchprocess_job()
        self.assertPOST409(self._build_delete_url(job))

    def test_clear04(self):
        "Credentials"
        self.login(is_superuser=False)

        job = self._create_batchprocess_job(user=self.other_user, status=Job.STATUS_OK)
        self.assertPOST403(self._build_delete_url(job))

        job = self._create_batchprocess_job(status=Job.STATUS_OK)
        self.assertPOST200(self._build_delete_url(job), follow=True)

    def test_clear05(self):
        "Can not clear a system job"
        self.login()

        job = Job.objects.create(type_id=batch_process_type.id, status=Job.STATUS_OK)  # No user -> system job
        self.assertPOST409(self._build_delete_url(job))

    def test_disable01(self):
        queue = JobManagerQueue.get_main_queue()
        queue.clear()

        self.login()
        self.assertEqual([], queue.refreshed_jobs)

        job = Job.objects.create(type_id=batch_process_type.id)  # No user -> system job
        self.assertIs(job.enabled, True)
        self.assertEqual([], queue.refreshed_jobs)

        disable_url = self._build_disable_url(job)
        self.assertGET404(disable_url)

        self.assertPOST200(disable_url)
        self.assertIs(self.refresh(job).enabled, False)
        self.assertEqual([job], queue.refreshed_jobs)

        enable_url = self._build_enable_url(job)
        self.assertGET404(enable_url)

        self.assertPOST200(enable_url)
        self.assertIs(self.refresh(job).enabled, True)

    def test_disable02(self):
        "Cannot disable a non-system job"
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
        self.assertEqual('text/javascript', response['Content-Type'])
        self.assertEqual({str(job.id): {'status': Job.STATUS_WAIT,
                                        'ack_errors': 0,
                                       }
                         },
                         json_load(response.content)
                        )

        job = self._create_batchprocess_job(status=Job.STATUS_OK)
        response = self.assertGET200(url, data={'id': [job.id]})
        self.assertEqual({str(job.id): {'status': Job.STATUS_OK,
                                        'ack_errors': 0,
                                       }
                         },
                         json_load(response.content)
                        )

        job = self._create_batchprocess_job(user=self.other_user)
        response = self.assertGET200(url, data={'id': [job.id]})
        self.assertEqual({str(job.id): 'Job is not allowed'}, json_load(response.content))

        invalid_id = Job.objects.aggregate(Max('id'))['id__max'] + 1
        response = self.assertGET200(url, data={'id': [invalid_id]})
        self.assertEqual({str(invalid_id): 'Invalid job ID'}, json_load(response.content))

        invalid_id = 'invalid'
        response = self.assertGET200(url, data={'id': [invalid_id]})
        self.assertEqual({}, json_load(response.content))

    def test_status02(self):
        "Several jobs"
        self.login(is_superuser=False)

        job1 = self._create_batchprocess_job()
        job2 = self._create_batchprocess_job(status=Job.STATUS_OK)
        job3 = self._create_batchprocess_job(user=self.other_user)
        response = self.assertGET200(self.INFO_URL, data={'id': [job1.id, job3.id, job2.id]})
        self.assertEqual({str(job1.id): {'status': Job.STATUS_WAIT, 'ack_errors': 0},
                          str(job2.id): {'status': Job.STATUS_OK, 'ack_errors': 0},
                          str(job3.id): 'Job is not allowed',
                         },
                         json_load(response.content)
                        )

    def test_status03(self):
        "Queue error"
        error = 'Arggggg'
        self.queue.ping = lambda: error

        self.login(is_superuser=False)

        response = self.assertGET200(self.INFO_URL)
        self.assertEqual({'error': error}, json_load(response.content))

    def test_status04(self):
        "ACK error"
        self.queue.start_job = lambda job: True
        self.login(is_superuser=False)

        job = self._create_batchprocess_job()
        self.assertEqual(1, self.refresh(job).ack_errors)

        response = self.assertGET200(self.INFO_URL, data={'id': [job.id]})
        self.assertEqual({str(job.id): {'status': Job.STATUS_WAIT,
                                        'ack_errors': 1,
                                       },
                         },
                         json_load(response.content)
                        )

    def _aux_test_reload(self, job, block_id):
        response = self.assertGET200('/creme_core/job/%s/reload/%s' % (job.id, block_id))

        with self.assertNoException():
            result = json_load(response.content)

        self.assertIsInstance(result, list)
        self.assertEqual(1, len(result))

        result = result[0]
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))
        self.assertEqual(block_id, result[0])
        self.assertIn(' id="%s"' % block_id, result[1])

    def test_reload01(self):
        self.login()
        job = self.get_object_or_fail(Job, type_id=reminder_type.id)

        self._aux_test_reload(job, job_block.id_)
        self._aux_test_reload(job, job_errors_block.id_)

    def test_reload02(self):
        self.login()
        job = self._create_batchprocess_job()

        self._aux_test_reload(job, job_block.id_)
        self._aux_test_reload(job, entity_job_errors_block.id_)

    def test_reload03(self):
        self.login(is_superuser=False)
        job = self._create_batchprocess_job(user=self.other_user)
        self.assertGET403('/creme_core/job/%s/reload/%s' % (job.id, job_block.id_))
