# -*- coding: utf-8 -*-

from functools import partial
from json import dumps as json_dump

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_filter import operands, operators
from creme.creme_core.core.entity_filter.condition_handler import (
    RegularFieldConditionHandler,
)
# Should be a test queue
# from creme.creme_core.core.job import JobSchedulerQueue, job_type_registry
from creme.creme_core.core.job import get_queue, job_type_registry
from creme.creme_core.creme_jobs.batch_process import batch_process_type
from creme.creme_core.models import (
    EntityFilter,
    EntityJobResult,
    FakeContact,
    FakeOrganisation,
    Job,
    SetCredentials,
)

from .base import ViewsTestCase


class BatchProcessViewsTestCase(ViewsTestCase):
    @classmethod
    def build_formfield_entry(cls, name, operator, value):
        return {'name': name, 'operator': operator, 'value': value}

    @classmethod
    def build_formfield_value(cls, name, operator, value):
        return json_dump([cls.build_formfield_entry(name, operator, value)])

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Job.objects.all().delete()

        get_ct = ContentType.objects.get_for_model
        cls.orga_ct       = get_ct(FakeOrganisation)
        cls.contact_ct_id = get_ct(FakeContact).id

    @staticmethod
    def _build_add_url(model, efilter_id=None):
        uri = reverse(
            'creme_core__batch_process',
            args=(ContentType.objects.get_for_model(model).id,),
        )

        if efilter_id:
            uri += f'?efilter={efilter_id}'

        return uri

    def _get_job(self, response):
        with self.assertNoException():
            return response.context['job']

    def _execute_job(self, response):
        batch_process_type.execute(self._get_job(response))

    def test_no_app_perm(self):
        # Not 'creme_core'
        self.login(is_superuser=False, allowed_apps=['documents'])
        self.assertGET403(self._build_add_url(FakeOrganisation))

    def test_app_perm(self):
        self.login(is_superuser=False, allowed_apps=['creme_core'])
        self.assertGET200(self._build_add_url(FakeOrganisation))

    @override_settings(MAX_JOBS_PER_USER=1)
    def test_max_job(self):
        user = self.login()
        Job.objects.create(
            user=user, type_id=batch_process_type.id, language='en',
        )

        response = self.assertGET200(self._build_add_url(FakeOrganisation), follow=True)
        self.assertRedirects(response, reverse('creme_core__my_jobs'))

    def test_batching_upper01(self):
        # queue = JobSchedulerQueue.get_main_queue()
        queue = get_queue()
        queue.clear()

        self.login()
        self.assertFalse(Job.objects.filter(type_id=batch_process_type.id))
        self.assertEqual([], queue.started_jobs)
        self.assertEqual([], queue.refreshed_jobs)

        url = self._build_add_url(FakeOrganisation)

        response = self.assertGET200(url)

        with self.assertNoException():
            form = response.context['form']
            orga_fields = {*form.fields['actions']._fields}

        self.assertDictEqual(
            {
                'content_type': self.orga_ct,
                'filter': None,
            },
            form.initial
        )

        self.assertIn('name', orga_fields)
        self.assertIn('capital', orga_fields)

        create_orga = partial(FakeOrganisation.objects.create, user=self.user)
        orga01 = create_orga(name='Genshiken')
        orga02 = create_orga(name='Manga club')

        response = self.client.post(
            url, follow=True,
            data={
                'actions': self.build_formfield_value(
                    operator='upper',
                    name='name',
                    value='',
                ),
            },
        )
        self.assertNoFormError(response)

        jobs = Job.objects.filter(type_id=batch_process_type.id)
        self.assertEqual(1, len(jobs))

        job = jobs[0]
        self.assertEqual(self.user, job.user)
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
        self.assertListEqual(
            [
                _('Entity type: {}').format('Test Organisation'),
                _('{field} ➔ {operator}').format(
                    field=_('Name'),
                    operator=_('To upper case'),
                )
            ],
            job.description,
        )

        self.assertRedirects(response, job.get_absolute_url())

        self.assertListEqual([job], queue.started_jobs)
        self.assertListEqual([], queue.refreshed_jobs)

        batch_process_type.execute(job)

        self.assertEqual('GENSHIKEN',  self.refresh(orga01).name)
        self.assertEqual('MANGA CLUB', self.refresh(orga02).name)

        job = self.refresh(job)
        self.assertDatetimesAlmostEqual(now(), job.last_run, 10)
        self.assertEqual(Job.STATUS_OK, job.status)
        self.assertIsNone(job.error)

        orga_count = FakeOrganisation.objects.count()
        self.assertListEqual(
            [
                ngettext(
                    '{count} entity has been successfully modified.',
                    '{count} entities have been successfully modified.',
                    orga_count
                ).format(count=orga_count),
            ],
            job.stats,
        )

        self.assertListEqual([], queue.refreshed_jobs)

    def test_batching_lower01(self):
        "Lower OP & use CT."
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact01 = create_contact(first_name='Saki',     last_name='Kasukabe')
        contact02 = create_contact(first_name='Harunobu', last_name='Madarame')

        response = self.client.post(
            self._build_add_url(FakeContact), follow=True,
            data={
                'actions': self.build_formfield_value(
                    name='first_name',
                    operator='lower',
                    value='',
                ),
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)

        self.assertEqual('saki',     self.refresh(contact01).first_name)
        self.assertEqual('harunobu', self.refresh(contact02).first_name)

    def test_batching_suffix(self):
        "Operator value + unicode char."
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        contact01 = create_contact(first_name='Saki',   last_name='Kasukabe')
        contact02 = create_contact(first_name='Kanako', last_name='Ono')

        response = self.client.post(
            self._build_add_url(FakeContact), follow=True,
            data={
                'actions': self.build_formfield_value(
                    name='first_name',
                    operator='suffix',
                    value='-adorée',
                ),
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)

        self.assertEqual('Saki-adorée',   self.refresh(contact01).first_name)
        self.assertEqual('Kanako-adorée', self.refresh(contact02).first_name)

    def test_validation_error01(self):
        "Invalid field."
        self.login()

        response = self.assertPOST200(
            self._build_add_url(FakeContact), follow=True,
            data={
                'actions': self.build_formfield_value(
                    name='unknown_field',  # <============= HERE
                    operator='lower',
                    value='',
                ),
            },
        )
        self.assertFormError(
            response, 'form', 'actions',
            _('This field is invalid with this model.'),
        )

# TODO: uncomment when a model has a field with batchable type and not inner
#       editable (maybe a test model)
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
#                             _('This field is invalid with this model.'),
#                            )

    def test_select_efilter(self):
        self.login()
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Contains "club"',
            FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation, field_name='name',
                    operator=operators.CONTAINS, values=['club'],
                ),
            ],
        )

        response = self.assertGET200(self._build_add_url(FakeOrganisation, efilter_id=efilter.id))

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(efilter.id, form.initial['filter'])

    def test_several_actions(self):
        "'upper' + 'title' operators."
        user = self.login()

        contact = FakeContact.objects.create(user=user, first_name='kanji', last_name='sasahara')
        response = self.client.post(
            self._build_add_url(FakeContact), follow=True,
            data={
                'actions': json_dump([
                    self.build_formfield_entry(name='first_name', operator='title', value=''),
                    self.build_formfield_entry(name='last_name',  operator='upper', value=''),
                ]),
            },
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
        response = self.assertPOST200(
            self._build_add_url(FakeContact), follow=True,
            data={
                'actions': json_dump([
                    self.build_formfield_entry(name=name, operator='title', value=''),
                    self.build_formfield_entry(name=name, operator='upper', value=''),
                ]),
            },
        )
        self.assertFormError(
            response, 'form', 'actions',
            _('The field «%(field)s» can not be used twice.') % {
                'field': _('First name'),
            },
        )

    def test_with_filter01(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga01 = create_orga(name='Genshiken')
        orga02 = create_orga(name='Manga club')
        orga03 = create_orga(name='Anime club')

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Contains "club"',
            FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation, field_name='name',
                    operator=operators.CONTAINS, values=['club'],
                ),
            ],
        )
        self.assertSetEqual(
            {orga02, orga03},
            {*efilter.filter(FakeOrganisation.objects.all())}
        )  # <== not 'orga01'

        response = self.client.post(
            self._build_add_url(FakeOrganisation), follow=True,
            data={
                'filter':  efilter.id,
                'actions': self.build_formfield_value(
                    name='name',
                    operator='lower',
                    value='',
                ),
            },
        )
        self.assertNoFormError(response)

        job = self._get_job(response)

        batch_process_type.execute(job)
        self.assertEqual('manga club', self.refresh(orga02).name)
        self.assertEqual('anime club', self.refresh(orga03).name)
        self.assertEqual('Genshiken',  self.refresh(orga01).name)  # <== not changed

        self.get_object_or_fail(EntityJobResult, job=job, entity=orga02)
        self.assertFalse(EntityJobResult.objects.filter(job=job, entity=orga01))
        self.assertListEqual(
            [
                ngettext(
                    '{count} entity has been successfully modified.',
                    '{count} entities have been successfully modified.',
                    2
                ).format(count=2),
            ],
            job.stats,
        )

        progress = job.progress
        self.assertIsNone(progress.percentage)
        self.assertEqual(
            ngettext(
                '{count} entity has been processed.',
                '{count} entities have been processed.',
                2
            ).format(count=2),
            progress.label,
        )

    def test_with_filter02(self):
        "Private filters (which belong to other users) are forbidden."
        self.login()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Contains "club"',
            FakeOrganisation, is_custom=True,
            is_private=True, user=self.other_user,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation, field_name='name',
                    operator=operators.CONTAINS, values=['club'],
                ),
            ],
        )

        response = self.assertPOST200(
            self._build_add_url(FakeOrganisation), follow=True,
            data={
                'filter':  efilter.id,
                'actions': self.build_formfield_value(
                    name='name',
                    operator='lower',
                    value='',
                ),
            },
        )
        self.assertFormError(
            response, 'form', 'filter',
            _(
                'Select a valid choice. '
                'That choice is not one of the available choices.'
            ),
        )

    def test_with_filter03(self):
        "__currentuser__ condition (need global_info)."
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga01 = create_orga(name='Genshiken')
        orga02 = create_orga(name='Manga club')
        orga03 = create_orga(name='Anime club', user=self.other_user)

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Assigned to me',
            FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation, field_name='user',
                    operator=operators.EQUALS,
                    values=[operands.CurrentUserOperand.type_id],
                ),
            ],
        )

        response = self.client.post(
            self._build_add_url(FakeOrganisation), follow=True,
            data={
                'filter':  efilter.id,
                'actions': self.build_formfield_value(
                    name='name',
                    operator='upper',
                    value='',
                ),
            },
        )
        self.assertNoFormError(response)

        job = self._get_job(response)
        job_type_registry(job.id)

        self.assertEqual('GENSHIKEN',  self.refresh(orga01).name)
        self.assertEqual('MANGA CLUB', self.refresh(orga02).name)
        self.assertEqual('Anime club', self.refresh(orga03).name)  # <== not changed

    def test_use_edit_perm(self):
        user = self.login(is_superuser=False)

        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),  # Not 'CHANGE'
            set_type=SetCredentials.ESET_ALL,
        )
        create_sc(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        create_orga = FakeOrganisation.objects.create
        orga01 = create_orga(user=self.other_user, name='Genshiken')
        orga02 = create_orga(user=user,            name='Manga club')

        self.assertFalse(self.user.has_perm_to_change(orga01))  # <== user cannot change
        self.assertTrue(self.user.has_perm_to_change(orga02))

        response = self.client.post(
            self._build_add_url(FakeOrganisation), follow=True,
            data={
                'actions': self.build_formfield_value(
                    name='name',
                    operator='lower',
                    value='',
                ),
            },
        )
        self.assertNoFormError(response)
        job = self._get_job(response)

        batch_process_type.execute(job)
        self.assertEqual('manga club', self.refresh(orga02).name)
        self.assertEqual('Genshiken',  self.refresh(orga01).name)  # <== not changed

        self.assertListEqual(
            [orga02],
            [
                jr.entity.get_real_entity()
                for jr in EntityJobResult.objects.filter(job=job)
            ],
        )

    def test_model_error(self):
        user = self.login()

        description = 'Genshiken member'
        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Belongs to Genshiken',
            FakeContact, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeContact,
                    field_name='description',
                    operator=operators.EQUALS,
                    values=[description],
                ),
            ],
        )

        first_name = 'Kanako'
        last_name = 'Ouno'
        create_contact = partial(FakeContact.objects.create, user=user, description=description)
        contact01 = create_contact(first_name=first_name, last_name=last_name)
        create_contact(first_name='Mitsunori', last_name='Kugayama')

        with self.assertRaises(ValidationError):
            contact01.last_name = ''
            contact01.full_clean()

        response = self.client.post(
            self._build_add_url(FakeContact), follow=True,
            data={
                'filter':  efilter.id,
                'actions': json_dump([
                    self.build_formfield_entry(name='last_name',  operator='rm_start', value=6),
                    self.build_formfield_entry(name='first_name', operator='upper',    value=''),
                ]),
            },
        )
        self.assertNoFormError(response)
        job = self._get_job(response)

        batch_process_type.execute(job)
        contact01 = self.refresh(contact01)
        self.assertEqual(last_name,  contact01.last_name)  # No change !!
        # TODO: make the changes that are possible ('KANAKO') ??
        self.assertEqual(first_name, contact01.first_name)

        jresult = self.get_object_or_fail(EntityJobResult, job=job, entity=contact01)
        self.assertListEqual(
            ['{} => {}'.format(_('Last name'), _('This field cannot be blank.'))],
            jresult.messages,
        )

        self.assertListEqual(
            [
                ngettext(
                    '{count} entity has been successfully modified.',
                    '{count} entities have been successfully modified.',
                    1
                ).format(count=1),
            ],
            job.stats,
        )

    def build_ops_url(self, ct_id, field):
        return reverse('creme_core__batch_process_ops', args=(ct_id, field))

    def test_get_ops01(self):
        "Unknown ContentType."
        self.login()
        self.assertGET404(self.build_ops_url(ct_id=1216545, field='name'))

    def test_get_ops02(self):
        "CharField."
        self.login()

        def assertStrOps(fieldname):
            response = self.assertGET200(self.build_ops_url(self.contact_ct_id, fieldname))

            json_data = response.json()
            self.assertIsList(json_data)
            self.assertTrue(json_data)
            self.assertIn(['upper', _('To upper case')], json_data)
            self.assertIn(['lower', _('To lower case')], json_data)
            self.assertNotIn('add_int', (e[0] for e in json_data))

        assertStrOps('first_name')
        assertStrOps('email')

    def test_get_ops03(self):
        "Organisation CT, other category of operator."
        self.login()

        response = self.assertGET200(self.build_ops_url(self.orga_ct.id, 'capital'))

        json_data = response.json()
        self.assertIn(['add_int', _('Add')], json_data)
        self.assertIn(['sub_int', _('Subtract')], json_data)
        self.assertNotIn('prefix', (e[0] for e in json_data))

    def test_get_ops04(self):
        "Empty category."
        self.login()

        response = self.assertGET200(self.build_ops_url(self.contact_ct_id, 'image'))
        self.assertListEqual([], response.json())

    def test_get_ops05(self):
        "No app credentials."
        self.login(is_superuser=False, allowed_apps=['documents'])  # Not 'creme_core'
        self.assertGET403(self.build_ops_url(self.contact_ct_id, 'first_name'))

    def test_get_ops06(self):
        "Unknown field."
        self.login()
        self.assertGET(400, self.build_ops_url(self.contact_ct_id, 'foobar'))

    def test_resume_job(self):
        user = self.login()

        create_orga = partial(FakeOrganisation.objects.create, user=user, description='club')
        orga01 = create_orga(name='Coding club')
        orga02 = create_orga(name='Manga club')
        orga03 = create_orga(name='Anime club')

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Contains "club"', FakeOrganisation, is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation,
                    operator=operators.CONTAINS,
                    field_name='description',
                    values=['club'],
                ),
            ],
        )
        self.assertSetEqual(
            {orga01, orga02, orga03},
            {*efilter.filter(FakeOrganisation.objects.all())},
        )

        response = self.client.post(
            self._build_add_url(FakeOrganisation), follow=True,
            data={
                'filter':  efilter.id,
                'actions': self.build_formfield_value(
                    name='name',
                    operator='rm_end',
                    value='5',
                ),
            },
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

        response = self.client.post(
            self._build_add_url(FakeOrganisation), follow=True,
            data={
                'actions': self.build_formfield_value(
                    name='name',
                    operator='upper',
                    value='',
                ),
            },
        )
        self.assertNoFormError(response)

        response = self.assertGET200(self._build_add_url(FakeOrganisation), follow=True)
        self.assertRedirects(response, reverse('creme_core__my_jobs'))

    def test_fatalerror(self):
        self.login()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Contains "club"', FakeOrganisation, is_custom=True,
        )
        response = self.client.post(
            self._build_add_url(FakeOrganisation), follow=True,
            data={
                'filter':  efilter.id,
                'actions': self.build_formfield_value(
                    name='name',
                    operator='rm_end',
                    value='5',
                ),
            },
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
