from functools import partial
from json import dumps as json_dump

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core import workflows
from creme.creme_core.core.entity_filter import operands, operators
from creme.creme_core.core.entity_filter.condition_handler import (
    RegularFieldConditionHandler,
)
# Should be a test queue
from creme.creme_core.core.job import get_queue, job_type_registry
from creme.creme_core.core.workflow import WorkflowConditions, WorkflowEngine
from creme.creme_core.creme_jobs.batch_process import batch_process_type
from creme.creme_core.models import (
    CremePropertyType,
    EntityFilter,
    EntityJobResult,
    FakeContact,
    FakeOrganisation,
    Job,
    Workflow,
)

from ..base import CremeTestCase


class BatchProcessViewsTestCase(CremeTestCase):
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
        self.login_as_standard(allowed_apps=['documents'])
        self.assertGET403(self._build_add_url(FakeOrganisation))

    def test_app_perm(self):
        self.login_as_standard(allowed_apps=['creme_core'])
        self.assertGET200(self._build_add_url(FakeOrganisation))

    @override_settings(MAX_JOBS_PER_USER=1)
    def test_max_job(self):
        self.login_as_root()
        Job.objects.create(
            user=self.get_root_user(), type_id=batch_process_type.id, language='en',
        )

        response = self.assertGET200(self._build_add_url(FakeOrganisation), follow=True)
        self.assertRedirects(response, reverse('creme_core__my_jobs'))

    def test_batching_upper01(self):
        queue = get_queue()
        queue.clear()

        self.login_as_root()
        user = self.get_root_user()

        self.assertFalse(Job.objects.filter(type_id=batch_process_type.id))
        self.assertEqual([], queue.started_jobs)
        self.assertEqual([], queue.refreshed_jobs)

        url = self._build_add_url(FakeOrganisation)

        response = self.assertGET200(url)
        form = self.get_form_or_fail(response)

        with self.assertNoException():
            orga_fields = {*form.fields['actions']._fields}

        self.assertDictEqual(
            {
                'content_type': self.orga_ct,
                'filter': None,
            },
            form.initial,
        )

        self.assertIn('name', orga_fields)
        self.assertIn('capital', orga_fields)

        create_orga = partial(FakeOrganisation.objects.create, user=user)
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

        job = self.get_alone_element(Job.objects.filter(type_id=batch_process_type.id))
        self.assertEqual(user, job.user)
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
                ),
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
        self.login_as_root()

        create_contact = partial(FakeContact.objects.create, user=self.get_root_user())
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
        self.login_as_root()

        create_contact = partial(FakeContact.objects.create, user=self.get_root_user())
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
        self.login_as_root()

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
            self.get_form_or_fail(response),
            field='actions',
            errors=_('This field is invalid with this model.'),
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
        self.login_as_root()
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

        form = self.get_form_or_fail(response)
        self.assertEqual(efilter.id, form.initial['filter'])

    def test_several_actions(self):
        "'upper' + 'title' operators."
        self.login_as_root()

        contact = FakeContact.objects.create(
            user=self.get_root_user(), first_name='kanji', last_name='sasahara',
        )
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
        "Several times the same field."
        self.login_as_root()

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
            self.get_form_or_fail(response),
            field='actions',
            errors=_('The field «%(field)s» can not be used twice.') % {
                'field': _('First name'),
            },
        )

    def test_with_filter01(self):
        self.login_as_root()

        create_orga = partial(FakeOrganisation.objects.create, user=self.get_root_user())
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
        self.assertCountEqual(
            [orga02, orga03],
            efilter.filter(FakeOrganisation.objects.all()),
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
        self.login_as_root()

        efilter = EntityFilter.objects.smart_update_or_create(
            'test-filter01', 'Contains "club"',
            FakeOrganisation, is_custom=True,
            is_private=True, user=self.create_user(),
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
            self.get_form_or_fail(response),
            field='filter',
            errors=_(
                'Select a valid choice. '
                'That choice is not one of the available choices.'
            ),
        )

    def test_with_filter03(self):
        "__currentuser__ condition (need global_info)."
        user = self.login_as_root_and_get()

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga01 = create_orga(name='Genshiken')
        orga02 = create_orga(name='Manga club')
        orga03 = create_orga(name='Anime club', user=self.create_user())

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

    def test_workflow(self):
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is rich')

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        orga1 = create_orga(name='Anime club', capital=1_000)
        orga2 = create_orga(name='Manga club', capital=9_500)

        efilter = EntityFilter.objects.smart_update_or_create(
            pk='test-filter01', name='Contains "club"', model=FakeOrganisation,
            is_custom=True,
            conditions=[
                RegularFieldConditionHandler.build_condition(
                    model=FakeOrganisation, field_name='name',
                    operator=operators.CONTAINS, values=['club'],
                ),
            ],
        )

        source = workflows.EditedEntitySource(model=FakeOrganisation)
        Workflow.objects.create(
            title='WF for Organisation',
            content_type=FakeOrganisation,
            trigger=workflows.EntityEditionTrigger(model=FakeOrganisation),
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[
                    RegularFieldConditionHandler.build_condition(
                        model=FakeOrganisation,
                        operator=operators.GTEOperator, field_name='capital', values=[10_000],
                    ),
                ],
            ),
            actions=[workflows.PropertyAddingAction(entity_source=source, ptype=ptype)],
        )

        response = self.client.post(
            self._build_add_url(FakeOrganisation), follow=True,
            data={
                'filter':  efilter.id,
                'actions': self.build_formfield_value(
                    name='capital',
                    operator='add_int',
                    value='1000',
                ),
            },
        )
        self.assertNoFormError(response)

        batch_process_type.execute(self._get_job(response))
        orga1 = self.refresh(orga1)
        self.assertEqual(2_000, orga1.capital)
        self.assertHasNoProperty(entity=orga1, ptype=ptype)

        orga2 = self.refresh(orga2)
        self.assertEqual(10_500, orga2.capital)
        self.assertHasProperty(entity=orga2, ptype=ptype)

    def test_use_edit_perm(self):
        user = self.login_as_standard()
        self.add_credentials(user.role, all='!CHANGE', own='*')

        create_orga = FakeOrganisation.objects.create
        orga01 = create_orga(user=self.get_root_user(), name='Genshiken')
        orga02 = create_orga(user=user,                 name='Manga club')

        self.assertFalse(user.has_perm_to_change(orga01))  # <== user cannot change
        self.assertTrue(user.has_perm_to_change(orga02))

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
        self.login_as_root()

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
        create_contact = partial(
            FakeContact.objects.create,
            user=self.get_root_user(), description=description,
        )
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
        self.login_as_root()
        self.assertGET404(self.build_ops_url(ct_id=1216545, field='name'))

    def test_get_ops02(self):
        "CharField."
        self.login_as_root()

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
        self.login_as_root()

        response = self.assertGET200(self.build_ops_url(self.orga_ct.id, 'capital'))

        json_data = response.json()
        self.assertIn(['add_int', _('Add')], json_data)
        self.assertIn(['sub_int', _('Subtract')], json_data)
        self.assertNotIn('prefix', (e[0] for e in json_data))

    def test_get_ops04(self):
        "Empty category."
        self.login_as_root()

        response = self.assertGET200(self.build_ops_url(self.contact_ct_id, 'image'))
        self.assertListEqual([], response.json())

    def test_get_ops05(self):
        "No app credentials."
        self.login_as_standard(allowed_apps=['documents'])  # Not 'creme_core'
        self.assertGET403(self.build_ops_url(self.contact_ct_id, 'first_name'))

    def test_get_ops06(self):
        "Unknown field."
        self.login_as_root()
        self.assertGET(400, self.build_ops_url(self.contact_ct_id, 'foobar'))

    def test_resume_job(self):
        self.login_as_root()

        create_orga = partial(
            FakeOrganisation.objects.create,
            user=self.get_root_user(), description='club',
        )
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
        EntityJobResult.objects.create(job=job, real_entity=orga01)

        # Empty the Queue to avoid log messages
        WorkflowEngine.get_current()._queue.pickup()

        batch_process_type.execute(job)
        self.assertEqual('Manga',   self.refresh(orga02).name)
        self.assertEqual('Anime',   self.refresh(orga03).name)
        self.assertEqual('Coding',  self.refresh(orga01).name)  # <== Should not be modified again

    @override_settings(MAX_JOBS_PER_USER=1)
    def test_job_limit(self):
        self.login_as_root()

        response1 = self.client.post(
            self._build_add_url(FakeOrganisation), follow=True,
            data={
                'actions': self.build_formfield_value(
                    name='name',
                    operator='upper',
                    value='',
                ),
            },
        )
        self.assertNoFormError(response1)

        response2 = self.assertGET200(self._build_add_url(FakeOrganisation), follow=True)
        self.assertRedirects(response2, reverse('creme_core__my_jobs'))

    def test_fatalerror(self):
        self.login_as_root()

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
