# -*- coding: utf-8 -*-

try:
    from functools import partial
    from json import loads as load_json

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.core.exceptions import ValidationError
    from django.core.urlresolvers import reverse
    from django.test.utils import override_settings
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _, ungettext

    from .base import ViewsTestCase
    from ..fake_models import FakeContact as Contact, FakeOrganisation as Organisation
    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.core.job import job_type_registry, JobManagerQueue  # Should be a test queue
    from creme.creme_core.creme_jobs.batch_process import batch_process_type
    from creme.creme_core.models import (EntityFilter, EntityFilterCondition,
            SetCredentials, Job, EntityJobResult)
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class BatchProcessViewsTestCase(ViewsTestCase):
    format_str1 = '[{"name": "%(name)s", "operator": "%(operator)s", "value": "%(value)s"}]'
    format_str2 = '[{"name": "%(name01)s", "operator": "%(operator01)s", "value": "%(value01)s"},' \
                  ' {"name": "%(name02)s", "operator": "%(operator02)s", "value": "%(value02)s"}]'

    @classmethod
    def setUpClass(cls):
        # ViewsTestCase.setUpClass()
        super(BatchProcessViewsTestCase, cls).setUpClass()
        # cls.populate('creme_core')
        Job.objects.all().delete()

        get_ct = ContentType.objects.get_for_model
        cls.orga_ct       = get_ct(Organisation)
        cls.contact_ct_id = get_ct(Contact).id

    # def build_url(self, model):
    def _build_add_url(self, model):
        # return '/creme_core/list_view/batch_process/%s?list_url=%s' % (
        #                 ContentType.objects.get_for_model(model).id,
        #                 model.get_lv_absolute_url(),
        #              )
        return reverse('creme_core__batch_process',
                       args=(ContentType.objects.get_for_model(model).id,),
                      ) + '?list_url=' + model.get_lv_absolute_url()

    def _get_job(self, response):
        with self.assertNoException():
            return response.context['job']

    def _execute_job(self, response):
        batch_process_type.execute(self._get_job(response))

    def test_no_app_perm(self):
        self.login(is_superuser=False, allowed_apps=['documents'])  # Not 'creme_core'
        self.assertGET403(self._build_add_url(Organisation))

    def test_app_perm(self):
        self.login(is_superuser=False, allowed_apps=['creme_core'])
        self.assertGET200(self._build_add_url(Organisation))

    @override_settings(MAX_JOBS_PER_USER=1)
    def test_max_job(self):
        user = self.login()
        Job.objects.create(user=user,
                           type_id=batch_process_type.id,
                           language='en',
                          )

        response = self.assertGET200(self._build_add_url(Organisation), follow=True)
        # self.assertRedirects(response, '/creme_core/job/all')
        self.assertRedirects(response, reverse('creme_core__jobs'))

    def test_batching_upper01(self):
        queue = JobManagerQueue.get_main_queue()
        queue.clear()

        self.login()
        self.assertFalse(Job.objects.filter(type_id=batch_process_type.id))
        self.assertEqual([], queue.started_jobs)
        self.assertEqual([], queue.refreshed_jobs)

        url = self._build_add_url(Organisation)

        response = self.assertGET200(url)

        with self.assertNoException():
            form = response.context['form']
            orga_fields = set(form.fields['actions']._fields.iterkeys())

        self.assertEqual({'content_type': self.orga_ct,
                          'filter': None,
                         },
                         form.initial
                        )

        self.assertIn('name', orga_fields)
        self.assertIn('capital', orga_fields)

        create_orga = partial(Organisation.objects.create, user=self.user)
        orga01 = create_orga(name='Genshiken')
        orga02 = create_orga(name='Manga club')

        response = self.client.post(url, follow=True,
                                    data={'actions': self.format_str1 % {
                                                            'operator': 'upper',
                                                            'name':     'name',
                                                            'value':    '',
                                                        },
                                         }
                                   )
        self.assertNoFormError(response)

        jobs = Job.objects.filter(type_id=batch_process_type.id)
        self.assertEqual(1, len(jobs))

        job = jobs[0]
        self.assertEqual(self.user, job.user)
        # # self.assertLess((now() - job.created).seconds, 1)
        # self.assertLess((now() - job.reference_run).seconds, 1)
        self.assertDatetimesAlmostEqual(now(), job.reference_run, 1)
        self.assertIsInstance(job.data, dict)
        self.assertEqual(Job.STATUS_WAIT, job.status)
        self.assertIsNone(job.error)
        self.assertFalse(EntityJobResult.objects.filter(job=job))
        self.assertIsNone(job.last_run)
        self.assertEqual(_('Core'), job.type.app_config.verbose_name)

        # Properties
        self.assertIs(batch_process_type, job.type)
        self.assertIs(False, job.is_finished)
        self.assertEqual([_('Entity type: %s') % 'Test Organisation',
                          _('%(field)s => %(operator)s') % {
                                'field':    _('Name'),
                                'operator': _('To upper case'),
                            }
                         ],
                         job.description
                        )

        self.assertRedirects(response, job.get_absolute_url())

        # with self.assertNoException():
        #     back_url = response.context['back_url'] TODO ? (if true, mass import too)
        #     form = response.context['form']
        #
        # self.assertEqual(u"http://testserver%s" % Organisation.get_lv_absolute_url(), back_url) TODO: ??

        self.assertEqual([job], queue.started_jobs)
        self.assertEqual([],    queue.refreshed_jobs)

        batch_process_type.execute(job)

        self.assertEqual('GENSHIKEN',  self.refresh(orga01).name)
        self.assertEqual('MANGA CLUB', self.refresh(orga02).name)

        # self.assertEqual(Organisation.get_lv_absolute_url(), back_url)
        job = self.refresh(job)
        # self.assertLess((now() - job.last_run).seconds, 10)
        self.assertDatetimesAlmostEqual(now(), job.last_run, 10)
        self.assertEqual(Job.STATUS_OK, job.status)
        self.assertIsNone(job.error)

        # self.assertIs(Organisation, form.entity_type)
        #
        # count = Organisation.objects.count()
        # self.assertEqual(count, form.modified_objects_count)
        # self.assertEqual(count, form.read_objects_count)
        # self.assertEqual(0,     len(form.process_errors))
        orga_count = Organisation.objects.count()
        self.assertEqual([ungettext('%s entity has been successfully modified.',
                                    '%s entities have been successfully modified.',
                                    orga_count
                                   ) % orga_count,
                         ],
                         job.stats
                        )

        self.assertEqual([], queue.refreshed_jobs)

    def test_batching_lower01(self):
        "Lower OP & use CT"
        user = self.login()

        create_contact = partial(Contact.objects.create, user=user)
        contact01 = create_contact(first_name='Saki',     last_name='Kasukabe')
        contact02 = create_contact(first_name='Harunobu', last_name='Madarame')

        response = self.client.post(self._build_add_url(Contact), follow=True,
                                    data={'actions': self.format_str1 % {
                                                            'name':     'first_name',
                                                            'operator': 'lower',
                                                            'value':    '',
                                                        },
                                         }
                                   )
        self.assertNoFormError(response)

        self._execute_job(response)

        self.assertEqual('saki',     self.refresh(contact01).first_name)
        self.assertEqual('harunobu', self.refresh(contact02).first_name)

        # with self.assertNoException():
        #     back_url = response.context['back_url']
        #     form = response.context['form']
        #
        # self.assertEqual(Contact.get_lv_absolute_url(), back_url)
        #
        # self.assertIs(Contact, form.entity_type)
        # self.assertFalse(form.process_errors)
        # self.assertEqual(Contact.objects.count(), form.modified_objects_count)

    def test_validation_error01(self):
        "Invalid field"
        self.login()

        response = self.assertPOST200(self._build_add_url(Contact), follow=True,
                                      data={'actions': self.format_str1 % {
                                                            'name':     'unknown_field',  # <============= HERE
                                                            'operator': 'lower',
                                                            'value':    '',
                                                        },
                                           }
                                     )
        self.assertFormError(response, 'form', 'actions',
                             _(u"This field is invalid with this model."),
                            )

# TODO: uncomment when a model has a field with batchable type and not inner editable (maybe a test model)
#    def test_validation_error02(self):
#        "Field is not inner editable -> invalid"
#        self.login()
#
#        fname = 'siren'
#        self.assertFalse(bulk_update_registry.is_updatable(
#                                Organisation, fname, exclude_unique=False,
#                            )
#                        )
#
#        response = self.assertPOST200(self._build_add_url(Organisation), follow=True,
#                                            data={'actions': self.format_str1 % {
#                                                                    'name':     fname,
#                                                                    'operator': 'lower',
#                                                                    'value':    '',
#                                                                },
#                                                 }
#                                     )
#        self.assertFormError(response, 'form', 'actions',
#                             _(u"This field is invalid with this model."),
#                            )

    def test_select_efilter(self):
        self.login()
        efilter = EntityFilter.create('test-filter01', 'Contains "club"',
                                      Organisation, is_custom=True,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=Organisation,
                                                        operator=EntityFilterCondition.CONTAINS,
                                                        name='name', values=['club'],
                                                    ),
                                                 ],
                                     )

        # We set the current list view state
        # Now needs a POST request for session changes.
        self.assertPOST200(Organisation.get_lv_absolute_url(), data={'filter': efilter.id})

        response = self.assertGET200(self._build_add_url(Organisation))

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(efilter.id, form.initial['filter'])

    def test_several_actions(self):
        "'upper' + 'title' operators"
        self.login()

        contact = Contact.objects.create(user=self.user, first_name='kanji', last_name='sasahara')
        response = self.client.post(self._build_add_url(Contact), follow=True,
                                    data={'actions': self.format_str2 % {
                                                        'name01': 'first_name', 'operator01': 'title', 'value01': '',
                                                        'name02': 'last_name',  'operator02': 'upper', 'value02': '',
                                                    },
                                         }
                                   )
        self.assertNoFormError(response)

        self._execute_job(response)
        contact = self.refresh(contact)
        self.assertEqual('Kanji',    contact.first_name)
        self.assertEqual('SASAHARA', contact.last_name)

    def test_several_actions_error(self):
        "Several times the same field"
        self.login()

        name = 'first_name'
        response = self.assertPOST200(self._build_add_url(Contact), follow=True,
                                      data={'actions': self.format_str2 % {
                                                            'name01': name, 'operator01': 'title', 'value01': '',
                                                            'name02': name, 'operator02': 'upper', 'value02': '',
                                                        },
                                           }
                                     )
        self.assertFormError(response, 'form', 'actions',
                             _(u"The field «%(field)s» can not be used twice.") % {
                                    'field': _('First name'),
                                 }
                            )

    def test_with_filter01(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='Genshiken')
        orga02 = create_orga(name='Manga club')
        orga03 = create_orga(name='Anime club')

        efilter = EntityFilter.create('test-filter01', 'Contains "club"',
                                      Organisation, is_custom=True,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=Organisation,
                                                        operator=EntityFilterCondition.CONTAINS,
                                                        name='name', values=['club'],
                                                    ),
                                                 ],
                                     )
        self.assertEqual({orga02, orga03}, set(efilter.filter(Organisation.objects.all())))  # <== not 'orga01'

        response = self.client.post(self._build_add_url(Organisation), follow=True,
                                    data={'filter':  efilter.id,
                                          'actions': self.format_str1 % {
                                                            'name':     'name',
                                                            'operator': 'lower',
                                                            'value':    '',
                                                        },
                                         }
                                   )
        self.assertNoFormError(response)

        job = self._get_job(response)

        batch_process_type.execute(job)
        self.assertEqual('manga club', self.refresh(orga02).name)
        self.assertEqual('anime club', self.refresh(orga03).name)
        self.assertEqual('Genshiken',  self.refresh(orga01).name)  # <== not changed

        # with self.assertNoException():
        #     form = response.context['form']
        #
        # self.assertEqual(2, form.modified_objects_count)
        self.get_object_or_fail(EntityJobResult, job=job, entity=orga02)
        self.assertFalse(EntityJobResult.objects.filter(job=job, entity=orga01))
        self.assertEqual([ungettext('%s entity has been successfully modified.',
                                    '%s entities have been successfully modified.',
                                    2
                                   ) % 2,
                         ],
                         job.stats
                        )

    def test_with_filter02(self):
        "Private filters (which belong to other users) are forbidden"
        self.login()

        efilter = EntityFilter.create('test-filter01', 'Contains "club"',
                                      Organisation, is_custom=True,
                                      is_private=True, user=self.other_user,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=Organisation,
                                                        operator=EntityFilterCondition.CONTAINS,
                                                        name='name', values=['club'],
                                                    ),
                                                 ],
                                     )

        response = self.assertPOST200(self._build_add_url(Organisation), follow=True,
                                    data={'filter':  efilter.id,
                                          'actions': self.format_str1 % {
                                                            'name':     'name',
                                                            'operator': 'lower',
                                                            'value':    '',
                                                        },
                                         }
                                   )
        self.assertFormError(response, 'form', 'filter',
                             _('Select a valid choice. That choice is not one of the available choices.')
                            )

    def test_with_filter03(self):
        "__currentuser__ condition (need global_info)"
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        orga01 = create_orga(name='Genshiken')
        orga02 = create_orga(name='Manga club')
        orga03 = create_orga(name='Anime club', user=self.other_user)

        efilter = EntityFilter.create('test-filter01', 'Assigned to me',
                                      Organisation, is_custom=True,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=Organisation,
                                                        operator=EntityFilterCondition.EQUALS,
                                                        name='user',
                                                        values=['__currentuser__'],
                                                    ),
                                                 ],
                                     )

        # NB: global_info must be set by the _JobTypeRegistry instance
        # from creme.creme_core.global_info import set_global_info
        # set_global_info(user=user)
        # self.assertEqual({orga01, orga02}, set(efilter.filter(Organisation.objects.all())))

        response = self.client.post(self._build_add_url(Organisation), follow=True,
                                    data={'filter':  efilter.id,
                                          'actions': self.format_str1 % {
                                                            'name':     'name',
                                                            'operator': 'upper',
                                                            'value':    '',
                                                        },
                                         }
                                   )
        self.assertNoFormError(response)

        job = self._get_job(response)

        # batch_process_type.execute(job)
        job_type_registry(job.id)

        self.assertEqual('GENSHIKEN',  self.refresh(orga01).name)
        self.assertEqual('MANGA CLUB', self.refresh(orga02).name)
        self.assertEqual('Anime club', self.refresh(orga03).name)  # <== not changed

    def test_use_edit_perm(self):
        user = self.login(is_superuser=False)

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(value=EntityCredentials.VIEW | EntityCredentials.DELETE |
                        EntityCredentials.LINK | EntityCredentials.UNLINK,  # Not 'CHANGE'
                  set_type=SetCredentials.ESET_ALL
                 )
        create_sc(value=EntityCredentials.VIEW | EntityCredentials.CHANGE | EntityCredentials.DELETE |
                        EntityCredentials.LINK | EntityCredentials.UNLINK,
                  set_type=SetCredentials.ESET_OWN
                 )

        create_orga = Organisation.objects.create
        orga01 = create_orga(user=self.other_user, name='Genshiken')
        orga02 = create_orga(user=user,            name='Manga club')

        self.assertFalse(self.user.has_perm_to_change(orga01))  # <== user cannot change
        self.assertTrue(self.user.has_perm_to_change(orga02))

        response = self.client.post(self._build_add_url(Organisation), follow=True,
                                    data={'actions': self.format_str1 % {
                                                            'name':     'name',
                                                            'operator': 'lower',
                                                            'value':    '',
                                                        },
                                         }
                                   )
        self.assertNoFormError(response)
        job = self._get_job(response)

        batch_process_type.execute(job)
        self.assertEqual('manga club', self.refresh(orga02).name)
        self.assertEqual('Genshiken',  self.refresh(orga01).name)  # <== not changed

        # self.assertEqual(1, response.context['form'].read_objects_count)
        self.assertEqual([orga02],
                         [jr.entity.get_real_entity()
                            for jr in EntityJobResult.objects.filter(job=job)
                         ]
                        )

    def test_model_error(self):
        user = self.login()

        description = 'Genshiken member'
        efilter = EntityFilter.create('test-filter01', 'Belongs to Genshiken',
                                      Contact, is_custom=True,
                                      conditions=[EntityFilterCondition.build_4_field(
                                                        model=Contact,
                                                        operator=EntityFilterCondition.EQUALS,
                                                        name='description',
                                                        values=[description],
                                                    )
                                                 ],
                                      )

        first_name = 'Kanako'
        last_name = 'Ouno'
        create_contact = partial(Contact.objects.create, user=user, description=description)
        contact01 = create_contact(first_name=first_name, last_name=last_name)
        create_contact(first_name='Mitsunori', last_name='Kugayama')

        entity_str = unicode(contact01)

        with self.assertRaises(ValidationError):
            contact01.last_name = ''
            contact01.full_clean()

        response = self.client.post(self._build_add_url(Contact), follow=True,
                                    data={'filter':  efilter.id,
                                          'actions': self.format_str2 % {
                                                            'name01': 'last_name',  'operator01': 'rm_start', 'value01': 6,
                                                            'name02': 'first_name', 'operator02': 'upper',    'value02': '',
                                                        },
                                         }
                                   )
        self.assertNoFormError(response)
        job = self._get_job(response)

        batch_process_type.execute(job)
        contact01 = self.refresh(contact01)
        self.assertEqual(last_name,  contact01.last_name)  # No change !!
        self.assertEqual(first_name, contact01.first_name)  # TODO: make the changes that are possible (u'KANAKO') ??

        # form = response.context['form']
        # self.assertEqual(1, form.modified_objects_count)
        # self.assertEqual(2, form.read_objects_count)
        jresult = self.get_object_or_fail(EntityJobResult, job=job, entity=contact01)
        self.assertEqual([u'%s => %s' % (_('Last name'), _(u'This field cannot be blank.'))],
                         jresult.messages
                        )

        # errors = form.process_errors
        # self.assertEqual(1, len(errors))
        #
        # error = iter(errors).next()
        # self.assertEqual(entity_str, error[0])
        # self.assertEqual([u'%s => %s' % (_('Last name'), _(u'This field cannot be blank.'))],
        #                  error[1]
        #                 )
        self.assertEqual([ungettext('%s entity has been successfully modified.',
                                    '%s entities have been successfully modified.',
                                    1
                                   ) % 1,
                         ],
                         job.stats
                        )

    def build_ops_url(self, ct_id, field):
        # return '/creme_core/list_view/batch_process/%(ct_id)s/get_ops/%(field)s' % {
        #                 'ct_id': ct_id,
        #                 'field': field,
        #             }
        return reverse('creme_core__batch_process_ops', args=(ct_id, field))

    def test_get_ops01(self):
        "Unknown ContentType"
        self.login()
        self.assertGET404(self.build_ops_url(ct_id=1216545, field='name'))

    def test_get_ops02(self):
        "CharField"
        self.login()

        def assertStrOps(fieldname):
            response = self.assertGET200(self.build_ops_url(self.contact_ct_id, fieldname))

            json_data = load_json(response.content)
            self.assertIsInstance(json_data, list)
            self.assertTrue(json_data)
            self.assertIn(['upper', _('To upper case')], json_data)
            self.assertIn(['lower', _('To lower case')], json_data)
            self.assertNotIn('add_int', (e[0] for e in json_data))

        assertStrOps('first_name')
        assertStrOps('email')

    def test_get_ops03(self):
        "Organisation CT, other category of operator"
        self.login()

        response = self.assertGET200(self.build_ops_url(self.orga_ct.id, 'capital'))

        json_data = load_json(response.content)
        self.assertIn(['add_int', _('Add')], json_data)
        self.assertIn(['sub_int', _('Subtract')], json_data)
        self.assertNotIn('prefix', (e[0] for e in json_data))

    def test_get_ops04(self):
        "Empty category"
        self.login()

        response = self.assertGET200(self.build_ops_url(self.contact_ct_id, 'image'))
        self.assertEqual([], load_json(response.content))

    def test_get_ops05(self):
        "No app credentials"
        self.login(is_superuser=False, allowed_apps=['documents'])  # Not 'creme_core'
        self.assertGET403(self.build_ops_url(self.contact_ct_id, 'first_name'))

    def test_get_ops06(self):
        "Unknown field"
        self.login()

        self.assertGET(400, self.build_ops_url(self.contact_ct_id, 'foobar'))

    def test_resume_job(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user, description='club')
        orga01 = create_orga(name='Coding club')
        orga02 = create_orga(name='Manga club')
        orga03 = create_orga(name='Anime club')

        efilter = EntityFilter.create('test-filter01', 'Contains "club"',
                                      Organisation, is_custom=True,
                                     )
        efilter.set_conditions([EntityFilterCondition.build_4_field(model=Organisation,
                                                                    operator=EntityFilterCondition.CONTAINS,
                                                                    name='description', values=['club']
                                                                   )
                               ])
        self.assertEqual({orga01, orga02, orga03},
                         set(efilter.filter(Organisation.objects.all()))
                        )

        response = self.client.post(self._build_add_url(Organisation), follow=True,
                                    data={'filter':  efilter.id,
                                          'actions': self.format_str1 % {
                                                            'name':     'name',
                                                            'operator': 'rm_end',
                                                            'value':    '5',
                                                        },
                                         }
                                   )
        self.assertNoFormError(response)

        job = self._get_job(response)

        # We simulate a job which has been interrupted
        orga01.name = 'Coding'
        orga01.save()
        EntityJobResult.objects.create(job=job, entity=orga01)

        batch_process_type.execute(job)
        self.assertEqual('Manga',   self.refresh(orga02).name)
        self.assertEqual('Anime',   self.refresh(orga03).name)
        self.assertEqual('Coding',  self.refresh(orga01).name)  # <== Should not be modified again

    def test_job_limit(self):
        settings.MAX_JOBS_PER_USER = 1

        self.login()

        response = self.client.post(self._build_add_url(Organisation), follow=True,
                                    data={'actions': self.format_str1 % {
                                                            'name':     'name',
                                                            'operator': 'upper',
                                                            'value':    '',
                                                        },
                                         }
                                   )
        self.assertNoFormError(response)

        response = self.assertGET200(self._build_add_url(Organisation), follow=True)
        # self.assertRedirects(response, '/creme_core/job/all')
        self.assertRedirects(response, reverse('creme_core__jobs'))

    def test_fatalerror(self):
        self.login()

        efilter = EntityFilter.create('test-filter01', 'Contains "club"',
                                      Organisation, is_custom=True,
                                    )
        response = self.client.post(self._build_add_url(Organisation), follow=True,
                                    data={'filter':  efilter.id,
                                          'actions': self.format_str1 % {
                                                            'name':     'name',
                                                            'operator': 'rm_end',
                                                            'value':    '5',
                                                        },
                                         }
                                   )
        efilter.delete()
        self.assertDoesNotExist(efilter)

        job = self._get_job(response)

        with self.assertNoException():
            batch_process_type.execute(job)

        self.assertEqual(Job.STATUS_ERROR, job.status)
        self.assertEqual(_('The filter does not exist anymore'), job.error)
        self.assertTrue(job.is_finished)

    # TODO: custom fields ??
