from decimal import Decimal
from functools import partial
from json import dumps as json_dump

from django.contrib.contenttypes.models import ContentType
from django.template.defaultfilters import slugify
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.encoding import smart_str
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from creme.creme_core import workflows
from creme.creme_core.constants import UUID_CHANNEL_JOBS
from creme.creme_core.core.entity_filter import condition_handler
from creme.creme_core.core.entity_filter.operators import EndsWithOperator
from creme.creme_core.core.workflow import WorkflowConditions
from creme.creme_core.creme_jobs import batch_process_type
from creme.creme_core.creme_jobs.mass_import import (
    MassImportJobErrorsBrick,
    mass_import_type,
)
from creme.creme_core.gui.job import JobErrorsBrick
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    CustomField,
    CustomFieldEnumValue,
    FakeAddress,
    FakeCivility,
    FakeContact,
    FakeEmailCampaign,
    FakeOrganisation,
    FakePosition,
    FakeSector,
    FakeTicket,
    FakeTicketPriority,
    FakeTicketStatus,
    FieldsConfig,
    Job,
    MassImportJobResult,
    Notification,
    Relation,
    RelationType,
    Workflow,
)
from creme.creme_core.notification import MassImportDoneContent
from creme.creme_core.utils import update_model_instance
from creme.creme_core.utils.xlrd_utils import XlrdReader
from creme.documents.models import Document
from creme.documents.tests.base import skipIfCustomDocument, skipIfCustomFolder

from ..base import CremeTestCase
from .base import BrickTestCaseMixin, MassImportBaseTestCaseMixin


@skipIfCustomDocument
@skipIfCustomFolder
class MassImportViewsTestCase(MassImportBaseTestCaseMixin,
                              BrickTestCaseMixin,
                              CremeTestCase):
    lv_import_data = {
        'step': 1,
        # 'document':   doc.id,
        # 'has_header': True,
        # 'user':       self.user.id,

        'first_name_colselect': 1,
        'last_name_colselect':  2,

        'civility_colselect':    0,
        'description_colselect': 0,
        'phone_colselect':       0,
        'mobile_colselect':      0,
        'position_colselect':    0,
        'sector_colselect':      0,
        'email_colselect':       0,
        'url_site_colselect':    0,
        'birthday_colselect':    0,
        'image_colselect':       0,

        'is_a_nerd_colselect':    0,
        'loves_comics_colselect': 0,
        'languages_colselect':    0,
        'preferred_countries_colselect': 0,

        # 'property_types',
        # 'fixed_relations',
        # 'dyn_relations',

        'address_value_colselect':      0,
        'address_zipcode_colselect':    0,
        'address_city_colselect':       0,
        'address_department_colselect': 0,
        'address_country_colselect':    0,
    }

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Job.objects.all().delete()

        cls.ct = ContentType.objects.get_for_model(FakeContact)

    @staticmethod
    def _build_dl_errors_url(job):
        return reverse('creme_core__dl_mass_import_errors', args=(job.id,))

    @staticmethod
    def _dyn_relations_value(rtype, model, column, subfield):
        return json_dump([{
            'rtype':       rtype.id,
            'ctype':       str(ContentType.objects.get_for_model(model).id),
            'column':      str(column),
            'searchfield': subfield,
        }])

    def _test_import01(self, builder):
        user = self.login_as_root_and_get()

        count = FakeContact.objects.count()
        lines = [
            ('Rei',   'Ayanami'),
            ('Asuka', 'Langley'),
        ]

        doc = builder(lines, user=user)
        url = self._build_import_url(FakeContact)
        response1 = self.assertGET200(url)
        self.get_form_or_fail(response1)

        # ---
        response2 = self.client.post(
            url,
            data={
                'step':     0,
                'document': doc.id,
                # has_header
            },
        )
        self.assertNoFormError(response2)

        form = self.get_form_or_fail(response2)
        self.assertIn('value="1"', str(form['step']))

        # ---
        response3 = self.client.post(
            url,
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
            },
        )
        self.assertNoFormError(response3)

        job = self.get_alone_element(Job.objects.all())
        self.assertEqual(user, job.user)
        self.assertIsNone(job.last_run)
        self.assertIsInstance(job.data, dict)
        self.assertEqual(Job.STATUS_WAIT, job.status)
        self.assertIsNone(job.error)
        self.assertFalse(self._get_job_results(job))

        # Properties
        self.assertIs(mass_import_type, job.type)
        self.assertListEqual(
            [_('Import «{model}» from {doc}').format(model='Test Contact', doc=doc)],
            job.description,
        )  # TODO: description of columns ????

        self.assertRedirects(response3, job.get_absolute_url())

        self.assertFalse(
            Notification.objects.filter(user=user, channel__uuid=UUID_CHANNEL_JOBS),
        )

        tree = self.get_html_tree(response3.content)
        self.get_brick_node(tree, brick=MassImportJobErrorsBrick)

        mass_import_type.execute(job)

        lines_count = len(lines)
        self.assertEqual(count + lines_count, FakeContact.objects.count())
        self.assertDatetimesAlmostEqual(now(), job.last_run)

        contacts = []
        for first_name, last_name in lines:
            contact = self.get_object_or_fail(
                FakeContact, first_name=first_name, last_name=last_name,
            )
            self.assertEqual(user, contact.user)
            self.assertIsNone(contact.address)

            contacts.append(contact)

        job = self.refresh(job)
        self.assertEqual(Job.STATUS_OK, job.status)
        self.assertIsNone(job.error)
        results = self._get_job_results(job)
        self.assertEqual(2, len(results))
        self.assertCountEqual(contacts, [r.entity.get_real_entity() for r in results])
        self._assertNoResultError(results)
        self.assertIs(results[0].updated, False)

        self.assertListEqual(
            [
                ngettext(
                    '{count} «{model}» has been created.',
                    '{count} «{model}» have been created.',
                    lines_count,
                ).format(
                    count=lines_count,
                    model='Test Contacts',
                ),
                ngettext(
                    '{count} line in the file.',
                    '{count} lines in the file.',
                    lines_count,
                ).format(count=lines_count),
            ],
            job.stats,
        )

        progress = job.progress
        self.assertIsNone(progress.percentage)
        self.assertEqual(
            ngettext(
                '{count} line has been processed.',
                '{count} lines have been processed.',
                lines_count,
            ).format(count=lines_count),
            progress.label,
        )

        notif = self.get_object_or_fail(
            Notification, user=user, channel__uuid=UUID_CHANNEL_JOBS,
        )
        self.assertEqual(MassImportDoneContent.id, notif.content_id)
        self.assertDictEqual({'instance': doc.id}, notif.content_data)
        self.assertEqual(
            _('The mass import for document «%(object)s» is done') % {'object': doc},
            notif.content.get_body(user),
        )

        # Reload brick -----------
        reload_url = reverse('creme_core__reload_job_bricks', args=(job.id,))
        brick_id = MassImportJobErrorsBrick.id
        response = self.assertGET200(reload_url, data={'brick_id': brick_id})

        with self.assertNoException():
            results = response.json()

        self.assertIsList(results, length=1)

        result = results[0]
        self.assertIsList(result, length=2)
        self.assertEqual(brick_id, result[0])

        tree = self.get_html_tree(result[1])
        self.get_brick_node(tree, brick_id)

        self.assertGET404(reload_url, data={'brick_id': JobErrorsBrick.id})

    def _test_import02(self, builder):
        """Use header, default value, model search and create, properties,
        fixed and dynamic relations.
        """
        user = self.login_as_root_and_get()

        pos_title  = 'Pilot'
        sctr_title = 'Army'
        self.assertFalse(FakePosition.objects.filter(title=pos_title).exists())
        self.assertFalse(FakeSector.objects.filter(title=sctr_title).exists())

        position_ids = [*FakePosition.objects.values_list('id', flat=True)]
        sector_ids   = [*FakeSector.objects.values_list('id', flat=True)]

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Really cute in her suit')
        ptype2 = create_ptype(text='Great accuracy').set_subject_ctypes(FakeContact)
        ptype3 = create_ptype(text='International').set_subject_ctypes(FakeOrganisation)
        ptype4 = create_ptype(text='Disabled', enabled=False)

        employed = RelationType.objects.builder(
            id='test-subject_employed_by', predicate='is an employee of',
        ).symmetric(id='test-object_employed_by', predicate='employs').get_or_create()[0]
        loves = RelationType.objects.builder(
            id='test-subject_loving', predicate='is loving',
        ).symmetric(id='test-object_loving', predicate='is loved by').get_or_create()[0]

        disabled_rtype = RelationType.objects.builder(
            id='test-subject_disabled', predicate='disabled', enabled=False,
        ).symmetric(id='test-object_disabled', predicate='whatever').get_or_create()[0]

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        shinji = FakeContact.objects.create(user=user, first_name='Shinji', last_name='Ikari')
        contact_count = FakeContact.objects.count()

        city = 'Tokyo'
        lines = [
            ('First name', 'Last name', 'Position', 'Sector',   'City', 'Organisation'),
            ('Rei',        'Ayanami',   pos_title,  sctr_title, city,   nerv.name),
            ('Asuka',      'Langley',   pos_title,  sctr_title, '',     ''),
        ]

        doc = builder(lines, user=user)
        url = self._build_import_url(FakeContact)
        response1 = self.client.post(
            url,
            data={
                'step':       0,
                'document':   doc.id,
                'has_header': True,
            },
        )
        self.assertNoFormError(response1)

        with self.assertNoException():
            form = response1.context['form']
            properties_choices = form.fields['property_types'].choices
            allowed_fixed_rtypes_ids = {
                *form.fields['fixed_relations'].allowed_rtypes.values_list('id', flat=True)
            }

        self.assertIn('value="1"',    str(form['step']))
        self.assertIn('value="True"', str(form['has_header']))

        self.assertInChoices(value=ptype1.id, label=ptype1.text, choices=properties_choices)
        self.assertInChoices(value=ptype2.id, label=ptype2.text, choices=properties_choices)
        self.assertNotInChoices(value=ptype3.id, choices=properties_choices)
        self.assertNotInChoices(value=ptype4.id, choices=properties_choices)

        self.assertIn(employed.id, allowed_fixed_rtypes_ids)
        self.assertIn(loves.id,    allowed_fixed_rtypes_ids)
        self.assertNotIn(disabled_rtype.id, allowed_fixed_rtypes_ids)

        # ----
        default_descr = 'A cute pilot'
        response2 = self.client.post(
            url, follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'has_header': True,
                'user': user.id,

                'description_colselect': 0,
                'description_defval': default_descr,

                'position_colselect': 3,
                'position_subfield': 'title',
                'position_defval': '',  # The browser POST an empty string
                # 'position_create': False,

                'sector_colselect': 4,
                'sector_subfield': 'title',
                'sector_defval': '',  # The browser POST an empty string
                'sector_create': True,

                'property_types': [ptype1.id],

                'fixed_relations': self.formfield_value_multi_relation_entity((loves, shinji)),
                'dyn_relations': self._dyn_relations_value(
                    employed, FakeOrganisation, 6, 'name',
                ),

                'address_city_colselect': 5,
            },
        )
        self.assertNoFormError(response2)

        job = self._execute_job(response2)

        lines_count = len(lines) - 1  # '-1' for header
        self.assertEqual(contact_count + lines_count, FakeContact.objects.count())

        self.assertFalse(FakePosition.objects.exclude(id__in=position_ids).exists())

        sector = self.get_alone_element(FakeSector.objects.exclude(id__in=sector_ids))
        self.assertEqual(sctr_title, sector.title)

        created_contacts = {}
        for first_name, last_name, pos_title, sector_title, city_name, __orga_name in lines[1:]:
            contact = self.get_object_or_fail(
                FakeContact, first_name=first_name, last_name=last_name,
            )
            created_contacts[first_name] = contact

            self.assertEqual(default_descr, contact.description)
            self.assertIsNone(contact.position)
            self.assertEqual(sector,      contact.sector)
            self.assertHasProperty(entity=contact, ptype=ptype1)
            self.assertHaveRelation(subject=contact, type=loves, object=shinji)

        self.assertHaveRelation(subject=created_contacts['Rei'], type=employed, object=nerv)
        self.assertHaveNoRelation(subject=created_contacts['Asuka'], type=employed, object=nerv)

        # Header must not be used
        self.assertFalse(FakeContact.objects.filter(last_name=lines[0][1]))

        rei = FakeContact.objects.get(first_name=lines[1][0])
        address = rei.address
        self.assertIsInstance(address, FakeAddress)
        self.assertEqual(city, address.city)

        results = self._get_job_results(job)
        self.assertEqual(lines_count, len(results))
        self.assertListEqual(
            [
                ngettext(
                    '{count} «{model}» has been created.',
                    '{count} «{model}» have been created.',
                    lines_count,
                ).format(count=lines_count, model='Test Contacts'),
                ngettext(
                    '{count} line in the file.',
                    '{count} lines in the file.',
                    lines_count,
                ).format(count=lines_count),
            ],
            job.stats,
        )
        self.assertTrue(all(r.messages for r in results))  # Sector not found

    def _test_import03(self, builder):
        "Create entities to link with them."
        user = self.login_as_root_and_get()
        contact_ids = [*FakeContact.objects.values_list('id', flat=True)]

        orga_name = 'Nerv'
        self.assertFalse(FakeOrganisation.objects.filter(name=orga_name))

        employed = RelationType.objects.smart_update_or_create(
            ('test-subject_employed_by', 'is an employee of'),
            ('test-object_employed_by',  'employs'),
        )[0]
        doc = builder([('Ayanami', 'Rei', orga_name)], user=user)
        response = self.client.post(
            self._build_import_url(FakeContact), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,

                'dyn_relations': self._dyn_relations_value(employed, FakeOrganisation, 3, 'name'),
                'dyn_relations_can_create': True,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        rei = self.get_alone_element(FakeContact.objects.exclude(id__in=contact_ids))
        employer = self.get_alone_element(
            Relation.objects.filter(subject_entity=rei, type=employed)
        ).real_object
        self.assertIsInstance(employer, FakeOrganisation)
        self.assertEqual(orga_name, employer.name)

        result = self.get_alone_element(self._get_job_results(job))
        self.assertFalse(result.messages)

    def test_not_registered(self):
        self.login_as_root()
        self.assertGET404(self._build_import_url(FakeEmailCampaign))

    def test_csv_import01(self):
        return self._test_import01(self._build_csv_doc)

    def test_csv_import02(self):
        return self._test_import02(self._build_csv_doc)

    def test_csv_import03(self):
        return self._test_import03(self._build_csv_doc)

    def test_xls_import01(self):
        return self._test_import01(self._build_xls_doc)

    def test_xls_import02(self):
        return self._test_import02(self._build_xls_doc)

    def test_xls_import03(self):
        return self._test_import03(self._build_xls_doc)

    def test_xlsx_import01(self):
        return self._test_import01(self._build_xlsx_doc)

    def test_xlsx_import02(self):
        return self._test_import02(self._build_xlsx_doc)

    def test_xlsx_import03(self):
        return self._test_import03(self._build_xlsx_doc)

    def test_csv__other_separator(self):
        "Other separator."
        user = self.login_as_root_and_get()
        contact_ids = [*FakeContact.objects.values_list('id', flat=True)]

        lines = [
            ('First name', 'Last name'),
            ('Unchô',      'Kan-u'),
            ('Gentoku',    'Ryûbi'),
        ]

        doc = self._build_csv_doc(lines, separator=';', user=user)
        url = self._build_import_url(FakeContact)
        response = self.client.post(
            url,
            data={
                'step':     0,
                'document': doc.id,
            },
        )
        self.assertNoFormError(response)
        self.assertIn('value="1"', str(self.get_form_or_fail(response)['step']))

        response = self.client.post(
            url,
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'has_header': True,
                'user': user.id,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(
            len(lines) - 1,
            FakeContact.objects.exclude(id__in=contact_ids).count(),
        )

        for first_name, last_name in lines[1:]:
            self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)

        results = self._get_job_results(job)
        self.assertEqual(2, len(results))
        self._assertNoResultError(results)

    def test_workflow(self):
        user = self.login_as_root_and_get()
        ptype = CremePropertyType.objects.create(text='Is cool')

        source = workflows.CreatedEntitySource(model=FakeContact)
        Workflow.objects.create(
            title='WF for Contact',
            content_type=FakeContact,
            trigger=workflows.EntityCreationTrigger(model=FakeContact),
            conditions=WorkflowConditions().add(
                source=source,
                conditions=[
                    condition_handler.RegularFieldConditionHandler.build_condition(
                        model=FakeContact,
                        operator=EndsWithOperator, field_name='email', values=['@acme.org'],
                    ),
                ],
            ),
            actions=[workflows.PropertyAddingAction(entity_source=source, ptype=ptype)],
        )

        lines = [
            # 'First name', 'Last name', 'Email'
            ('Unchô',      'Kan-u',      'kanu@acme.org'),
            ('Gentoku',    'Ryûbi',      ''),
        ]
        doc = self._build_csv_doc(lines, user=user)
        url = self._build_import_url(FakeContact)
        self.assertNoFormError(self.client.post(
            url, data={'step': 0, 'document': doc.id},
        ))

        response2 = self.client.post(
            url,
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'email_colselect': 3,
            },
        )
        self.assertNoFormError(response2)

        job = self._execute_job(response2)
        results = self._get_job_results(job)
        self.assertEqual(2, len(results))
        self._assertNoResultError(results)

        def get_contact(line):
            return self.get_object_or_fail(FakeContact, first_name=line[0], last_name=line[1])

        line1 = lines[0]
        contact1 = get_contact(line1)
        self.assertEqual(line1[2], contact1.email)
        self.assertHasProperty(entity=contact1, ptype=ptype)

        contact2 = get_contact(lines[1])
        self.assertFalse(contact2.email)
        self.assertHasNoProperty(entity=contact2, ptype=ptype)

    def test_duplicated_relations(self):
        "Same Relation in fixed & dynamic fields at creation."
        user = self.login_as_root_and_get()

        employed = RelationType.objects.builder(
            id='test-subject_employed_by', predicate='employed by',
        ).symmetric(id='test-object_employed_by', predicate='employs').get_or_create()[0]

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name)], user=user)
        response = self.client.post(
            self._build_import_url(FakeContact), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'fixed_relations': self.formfield_value_multi_relation_entity((employed, nerv)),
                'dyn_relations': self._dyn_relations_value(
                    employed, FakeOrganisation, 3, 'name',
                ),
            },
        )

        self._execute_job(response)

        rei = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertHaveRelation(subject=rei, type=employed, object=nerv)  # Not duplicate error

    def test_relations_with_property_constraint_object01(self):
        "Constraint on object."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is rich')
        employed = RelationType.objects.builder(
            id='test-subject_employed_by', predicate='employed by', models=[FakeContact],
        ).symmetric(
            id='test-object_employed_by', predicate='employs',
            models=[FakeOrganisation], properties=[ptype],
        ).get_or_create()[0]
        employs = employed.symmetric_type

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        nerv = create_orga(name='Nerv')  # No ptype

        seele = create_orga(name='Seele')
        CremeProperty.objects.create(type=ptype, creme_entity=seele)

        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name, seele.name)], user=user)

        # Fixed relation
        response1 = self.client.post(
            self._build_import_url(FakeContact), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'fixed_relations': self.formfield_value_multi_relation_entity(
                    (employed, nerv),
                    (employed, seele),
                ),
            },
        )
        self.assertFormError(
            response1.context['form'],
            field='fixed_relations',
            errors=Relation.error_messages['missing_subject_property'] % {
                'entity': nerv,
                'property': ptype,
                'predicate': employs.predicate,
            },
        )

        # Dynamic relation
        orga_ct_id = str(ContentType.objects.get_for_model(FakeOrganisation).id)
        response2 = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'dyn_relations': json_dump([
                    {
                        'rtype': employed.id,
                        'ctype': orga_ct_id,
                        'column': '3',
                        'searchfield': 'name',
                    }, {
                        'rtype': employed.id,
                        'ctype': orga_ct_id,
                        'column': '4',
                        'searchfield': 'name',
                    },
                ]),
            },
        )
        self.assertNoFormError(response2)

        job = self._execute_job(response2)
        rei = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertHaveRelation(subject=rei, type=employed, object=seele)
        self.assertHaveNoRelation(subject=rei, type=employed, object=nerv)

        result = self.get_alone_element(self._get_job_results(job))
        self.assertListEqual(
            [
                Relation.error_messages['missing_subject_property'] % {
                    'entity': nerv,
                    'predicate': employs.predicate,
                    'property': ptype.text,
                },
            ],
            result.messages,
        )

    def test_relations_with_property_constraint_object02(self):
        "Constraint on object (forbidden property type)."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Went bankrupt')
        employed = RelationType.objects.builder(
            id='test-subject_employed_by', predicate='employed by', models=[FakeContact],
        ).symmetric(
            id='test-object_employed_by', predicate='employs',
            models=[FakeOrganisation], forbidden_properties=[ptype],
        ).get_or_create()[0]
        employs = employed.symmetric_type

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        nerv = create_orga(name='Nerv')
        seele = create_orga(name='Seele')  # No ptype

        CremeProperty.objects.create(type=ptype, creme_entity=nerv)

        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name, seele.name)], user=user)

        # Fixed relation
        response1 = self.client.post(
            self._build_import_url(FakeContact), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'fixed_relations': self.formfield_value_multi_relation_entity(
                    (employed, nerv),
                    (employed, seele),
                ),
            },
        )
        self.assertFormError(
            response1.context['form'],
            field='fixed_relations',
            errors=Relation.error_messages['refused_subject_property'] % {
                'entity': nerv,
                'property': ptype,
                'predicate': employs.predicate,
            },
        )

        # Dynamic relation
        orga_ct_id = str(ContentType.objects.get_for_model(FakeOrganisation).id)
        response2 = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'dyn_relations': json_dump([
                    {
                        'rtype': employed.id,
                        'ctype': orga_ct_id,
                        'column': '3',
                        'searchfield': 'name',
                    }, {
                        'rtype': employed.id,
                        'ctype': orga_ct_id,
                        'column': '4',
                        'searchfield': 'name',
                    },
                ]),
            },
        )
        self.assertNoFormError(response2)

        job = self._execute_job(response2)
        rei = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertHaveRelation(subject=rei, type=employed, object=seele)
        self.assertHaveNoRelation(subject=rei, type=employed, object=nerv)

        result = self.get_alone_element(self._get_job_results(job))
        self.assertListEqual(
            [
                Relation.error_messages['refused_subject_property'] % {
                    'entity': nerv,
                    'predicate': employs.predicate,
                    'property': ptype.text,
                },
            ],
            result.messages,
        )

    def test_relations_with_property_constraint_subject01(self):
        "Constraint on subject: fixed relationships + error."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is a pilot')
        employed = RelationType.objects.builder(
            id='test-subject_employed_by', predicate='employed by',
            models=[FakeContact], properties=[ptype],
        ).symmetric(
            id='test-object_employed_by', predicate='employs', models=[FakeOrganisation],
        ).get_or_create()[0]

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name)], user=user)

        response = self.client.post(
            self._build_import_url(FakeContact), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'fixed_relations': self.formfield_value_multi_relation_entity((employed, nerv)),
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        rei = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertHaveNoRelation(subject=rei, type=employed, object=nerv)

        result = self.get_alone_element(self._get_job_results(job))
        self.assertListEqual(
            [
                Relation.error_messages['missing_subject_property'] % {
                    'entity': rei,
                    'predicate': employed.predicate,
                    'property': ptype.text,
                },
            ],
            result.messages,
        )

    def test_relations_with_property_constraint_subject02(self):
        "Constraint on subject: fixed relationships (OK)."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is a pilot')
        employed = RelationType.objects.builder(
            id='test-subject_employed_by', predicate='employed by',
            models=[FakeContact], properties=[ptype],
        ).symmetric(
            id='test-object_employed_by', predicate='employs', models=[FakeOrganisation],
        ).get_or_create()[0]

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name)], user=user)

        response = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'property_types': [ptype.id],
                'fixed_relations': self.formfield_value_multi_relation_entity((employed, nerv)),
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        rei = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertHaveRelation(subject=rei, type=employed, object=nerv)

    def test_relations_with_property_constraint_subject03(self):
        "Constraint on subject: dynamic relationships + error."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is a pilot')
        employed = RelationType.objects.builder(
            id='test-subject_employed_by', predicate='employed by',
            models=[FakeContact], properties=[ptype],
        ).symmetric(
            id='test-object_employed_by', predicate='employs', models=[FakeOrganisation],
        ).get_or_create()[0]

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name)], user=user)

        response = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'dyn_relations': self._dyn_relations_value(
                    employed, FakeOrganisation, 3, 'name',
                ),
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        rei = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertHaveNoRelation(subject=rei, type=employed, object=nerv)

        result = self.get_alone_element(self._get_job_results(job))
        self.assertListEqual(
            [
                Relation.error_messages['missing_subject_property'] % {
                    'entity': rei,
                    'predicate': employed.predicate,
                    'property': ptype.text,
                },
            ],
            result.messages,
        )

    def test_relations_with_property_constraint_subject04(self):
        "Constraint on subject: dynamic relationships (OK)."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Is a pilot')
        employed = RelationType.objects.builder(
            id='test-subject_employed_by', predicate='employed by',
            models=[FakeContact], properties=[ptype],
        ).symmetric(
            id='test-object_employed_by', predicate='employs', models=[FakeOrganisation],
        ).get_or_create()[0]
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name)], user=user)
        response = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'property_types': [ptype.id],
                'dyn_relations': self._dyn_relations_value(
                    employed, FakeOrganisation, 3, 'name',
                ),
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        rei = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertHaveRelation(subject=rei, type=employed, object=nerv)

    def test_relations_with_forbidden_property_constraint_subject01(self):
        "Fixed relationships + error."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Hates big robots')
        employed = RelationType.objects.builder(
            id='test-subject_employed_by', predicate='employed by',
            models=[FakeContact], forbidden_properties=[ptype],
        ).symmetric(
            id='test-object_employed_by', predicate='employs', models=[FakeOrganisation],
        ).get_or_create()[0]
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name)], user=user)
        response = self.client.post(
            self._build_import_url(FakeContact), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'property_types': [ptype.id],
                'fixed_relations': self.formfield_value_multi_relation_entity((employed, nerv)),
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        rei = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertHaveNoRelation(subject=rei, type=employed, object=nerv)

        result = self.get_alone_element(self._get_job_results(job))
        self.assertListEqual(
            [
                Relation.error_messages['refused_subject_property'] % {
                    'entity': rei,
                    'predicate': employed.predicate,
                    'property': ptype.text,
                },
            ],
            result.messages,
        )

    def test_relations_with_forbidden_property_constraint_subject02(self):
        "Fixed relationships (OK)."
        user = self.login_as_root_and_get()

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Hates big robots')
        ptype2 = create_ptype(text='Is a pilot')

        employed = RelationType.objects.builder(
            id='test-subject_employed_by', predicate='employed by',
            models=[FakeContact], forbidden_properties=[ptype1],
        ).symmetric(
            id='test-object_employed_by', predicate='employs', models=[FakeOrganisation],
        ).get_or_create()[0]
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')
        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name)], user=user)
        response = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'property_types': [ptype2.id],
                'fixed_relations': self.formfield_value_multi_relation_entity((employed, nerv)),
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        rei = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertHaveRelation(subject=rei, type=employed, object=nerv)

    def test_relations_with_forbidden_property_constraint_subject03(self):
        "Dynamic relationships + error."
        user = self.login_as_root_and_get()

        ptype = CremePropertyType.objects.create(text='Hates big robots')
        employed = RelationType.objects.builder(
            id='test-subject_employed_by', predicate='employed by',
            models=[FakeContact], forbidden_properties=[ptype],
        ).symmetric(
            id='test-object_employed_by', predicate='employs', models=[FakeOrganisation],
        ).get_or_create()[0]
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name)], user=user)
        response = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'property_types': [ptype.id],
                'dyn_relations': self._dyn_relations_value(
                    employed, FakeOrganisation, 3, 'name',
                ),
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        rei = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertHaveNoRelation(subject=rei, type=employed, object=nerv)

        result = self.get_alone_element(self._get_job_results(job))
        self.assertListEqual(
            [
                Relation.error_messages['refused_subject_property'] % {
                    'entity': rei,
                    'predicate': employed.predicate,
                    'property': ptype.text,
                },
            ],
            result.messages,
        )

    def test_relations_with_forbidden_property_constraint_subject04(self):
        "Constraint on subject: dynamic relationships (OK)."
        user = self.login_as_root_and_get()

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Hates big robots')
        ptype2 = create_ptype(text='Is a pilot')

        employed = RelationType.objects.builder(
            id='test-subject_employed_by', predicate='employed by',
            models=[FakeContact], forbidden_properties=[ptype1],
        ).symmetric(
            id='test-object_employed_by', predicate='employs', models=[FakeOrganisation],
        ).get_or_create()[0]
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name)], user=user)
        response = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'property_types': [ptype2.id],
                'dyn_relations': self._dyn_relations_value(
                    employed, FakeOrganisation, 3, 'name',
                ),
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        rei = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertHaveRelation(subject=rei, type=employed, object=nerv)

    def test_default_value(self):
        "Use default value when CSV value is empty (+ fix unicode bug)."
        user = self.login_as_root_and_get()

        first_name = 'Gentoku'
        last_name = 'Ryûbi'
        doc = self._build_csv_doc([(first_name, '')], user=user)
        response = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,

                'last_name_defval': last_name,
            },
        )
        self.assertNoFormError(response)

        with self.assertNoException():
            self._execute_job(response)

        self.get_object_or_fail(FakeContact, last_name=last_name, first_name=first_name)

    def _get_cf_values(self, cf, entity):
        return self.get_object_or_fail(cf.value_class, custom_field=cf, entity=entity)

    def test_mass_import_customfields01(self):
        "CustomField.INT, STR & FLOAT, update, cast error."
        user = self.login_as_root_and_get()

        create_cf = partial(CustomField.objects.create, content_type=self.ct)
        cf_int = create_cf(name='Size (cm)',   field_type=CustomField.INT)
        cf_dec = create_cf(name='Weight (kg)', field_type=CustomField.FLOAT)
        cf_str = create_cf(name='Nickname',    field_type=CustomField.STR)

        lines = [
            ('First name', 'Last name', 'Size',   'Weight'),
            ('Unchô',      'Kan-u',     '180',    '55'),
            ('Gentoku',    'Ryûbi',     '155',    ''),
            ('Hakufu',     'Sonsaku',   '',       '50.2'),
            ('Shimei',     'Ryomou',    'notint', '48'),
        ]

        kanu = FakeContact.objects.create(
            user=user,
            first_name=lines[1][0],
            last_name=lines[1][1],
        )
        cf_int.value_class(custom_field=cf_dec, entity=kanu).set_value_n_save(Decimal('56'))
        cf_str.value_class(custom_field=cf_str, entity=kanu).set_value_n_save('Kan')

        contact_ids = [*FakeContact.objects.values_list('id', flat=True)]

        doc = self._build_csv_doc(lines, user=user)
        response = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'has_header': True,
                'user': user.id,
                'key_fields': ['first_name', 'last_name'],

                f'custom_field-{cf_int.id}_colselect': 3,
                f'custom_field-{cf_str.id}_colselect': 0,
                f'custom_field-{cf_dec.id}_colselect': 4,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(
            len(lines) - 2,  # 2 = 1 header + 1 update
            FakeContact.objects.exclude(id__in=contact_ids).count()
        )

        def get_contact(line_index):
            line = lines[line_index]
            return self.get_object_or_fail(FakeContact, first_name=line[0], last_name=line[1])

        get_cf_values = self._get_cf_values
        self.assertEqual(180, get_cf_values(cf_int, kanu).value)
        self.assertEqual(Decimal('55'), get_cf_values(cf_dec, kanu).value)
        self.assertEqual('Kan', get_cf_values(cf_str, kanu).value)

        ryubi = get_contact(2)
        self.assertEqual(155, get_cf_values(cf_int, ryubi).value)
        self.assertFalse(cf_dec.value_class.objects.filter(entity=ryubi))

        sonsaku = get_contact(3)
        self.assertFalse(cf_int.value_class.objects.filter(entity=sonsaku))
        self.assertEqual(Decimal('50.2'), get_cf_values(cf_dec, sonsaku).value)

        ryomou = get_contact(4)
        self.assertFalse(cf_int.value_class.objects.filter(entity=ryomou))
        self.assertEqual(Decimal('48'), get_cf_values(cf_dec, ryomou).value)

        results = self._get_job_results(job)
        self.assertEqual(4, len(results))

        jr_error = self.get_alone_element(r for r in results if r.messages)
        self.assertEqual([*lines[4]], jr_error.line)
        self.assertListEqual(
            [_('Enter a whole number.')],  # TODO: add the field verbose name !!
            jr_error.messages,
        )
        self.assertEqual(ryomou.entity_type, jr_error.entity_ctype)
        self.assertEqual(ryomou, jr_error.entity.get_real_entity())
        self.assertEqual(ryomou, jr_error.real_entity)

    def test_mass_import_customfields02(self):
        "CustomField.ENUM/MULTI_ENUM (no creation of choice)."
        user = self.login_as_root_and_get()
        contact_ids = [*FakeContact.objects.values_list('id', flat=True)]

        create_cf = partial(CustomField.objects.create, content_type=self.ct)
        cf_enum1 = create_cf(name='Attack',  field_type=CustomField.ENUM)
        cf_enum2 = create_cf(name='Drink',   field_type=CustomField.ENUM)
        cf_menum = create_cf(name='Weapons', field_type=CustomField.MULTI_ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        punch = create_evalue(custom_field=cf_enum1, value='Punch')
        create_evalue(custom_field=cf_enum1, value='Kick')
        create_evalue(custom_field=cf_enum1, value='Hold')

        create_evalue(custom_field=cf_enum2, value='Punch')  # Try to annoy the search on 'punch'

        create_evalue(custom_field=cf_menum, value='Sword')
        spear = create_evalue(custom_field=cf_menum, value='Spear')

        lines = [
            ('First name', 'Last name', 'Attack',        'Weapons'),
            ('Hakufu',     'Sonsaku',   'punch',         ''),
            ('Unchô',      'Kan-u',     'strangulation', 'Spear'),
        ]

        doc = self._build_csv_doc(lines, user=user)
        response = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'has_header': True,
                'user': user.id,

                f'custom_field-{cf_enum1.id}_colselect': 3,
                f'custom_field-{cf_enum2.id}_colselect': 0,
                f'custom_field-{cf_menum.id}_colselect': 4,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(
            len(lines) - 1,  # 1 header
            FakeContact.objects.exclude(id__in=contact_ids).count()
        )

        def get_contact(line_index):
            line = lines[line_index]
            return self.get_object_or_fail(FakeContact, first_name=line[0], last_name=line[1])

        get_cf_values = self._get_cf_values
        sonsaku = get_contact(1)
        self.assertEqual(punch, get_cf_values(cf_enum1, sonsaku).value)

        kanu = get_contact(2)
        self.assertFalse(cf_enum1.value_class.objects.filter(entity=kanu))
        self.assertListEqual([spear], [*get_cf_values(cf_menum, kanu).value.all()])

        results = self._get_job_results(job)
        self.assertEqual(2, len(results))

        jr_error = self.get_alone_element(r for r in results if r.messages)
        self.assertEqual([*lines[2]], jr_error.line)
        self.assertListEqual(
            [
                _(
                    'Error while extracting value: the choice «{value}» '
                    'was not found in existing choices (column {column}). '
                    'Hint: fix your imported file, or configure the import to '
                    'create new choices.'
                ).format(
                    column=3,
                    value='strangulation',
                ),
            ],
            jr_error.messages,
        )
        self.assertEqual(kanu, jr_error.entity.get_real_entity())

    def test_mass_import_customfields03(self):
        "CustomField.ENUM (creation of choice if not found)."
        user = self.login_as_root_and_get()
        contact_ids = [*FakeContact.objects.values_list('id', flat=True)]

        create_cf = partial(CustomField.objects.create, content_type=self.ct)
        cf_enum  = create_cf(name='Attack',  field_type=CustomField.ENUM)
        cf_menum = create_cf(name='Weapons', field_type=CustomField.MULTI_ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        punch = create_evalue(custom_field=cf_enum,  value='Punch')
        sword = create_evalue(custom_field=cf_menum, value='Sword')

        lines = [
            ('First name', 'Last name', 'Attack',        'Weapons'),
            ('Hakufu',     'Sonsaku',   'punch',         'sword'),
            ('Unchô',      'Kan-u',     'strangulation', 'spear'),
            ('Gentoku',    'Ryûbi',     '',              ''),
        ]

        doc = self._build_csv_doc(lines, user=user)
        response = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'has_header': True,
                'user': user.id,

                f'custom_field-{cf_enum.id}_colselect': 3,
                f'custom_field-{cf_enum.id}_create':    True,

                f'custom_field-{cf_menum.id}_colselect': 4,
                f'custom_field-{cf_menum.id}_create':    True,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(
            len(lines) - 1,  # 1 header
            FakeContact.objects.exclude(id__in=contact_ids).count()
        )

        def get_contact(line_index):
            line = lines[line_index]
            return self.get_object_or_fail(FakeContact, first_name=line[0], last_name=line[1])

        get_cf_values = self._get_cf_values
        sonsaku = get_contact(1)
        self.assertEqual(punch,   get_cf_values(cf_enum, sonsaku).value)
        self.assertListEqual([sword], [*get_cf_values(cf_menum, sonsaku).value.all()])

        kanu = get_contact(2)
        strang = self.get_object_or_fail(
            CustomFieldEnumValue, custom_field=cf_enum, value='strangulation',
        )
        self.assertEqual(strang, get_cf_values(cf_enum, kanu).value)
        spear = self.get_object_or_fail(
            CustomFieldEnumValue, custom_field=cf_menum, value='spear',
        )
        self.assertListEqual([spear], [*get_cf_values(cf_menum, kanu).value.all()])

        self.assertEqual(
            2,
            CustomFieldEnumValue.objects.filter(custom_field=cf_enum).count()
        )  # Not '' choice

        self._assertNoResultError(self._get_job_results(job))

    def test_mass_import_customfields04(self):
        "CustomField.ENUM/MULTI_ENUM: creation credentials."
        user = self.login_as_standard(
            allowed_apps=['creme_core', 'documents'],
            creatable_models=[FakeContact, Document],
        )
        self.add_credentials(user.role, own='*')

        create_cf = partial(CustomField.objects.create, content_type=self.ct)
        cf_enum  = create_cf(name='Attack',  field_type=CustomField.ENUM)
        cf_menum = create_cf(name='Weapons', field_type=CustomField.MULTI_ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        create_evalue(custom_field=cf_enum,  value='Punch')
        create_evalue(custom_field=cf_menum, value='Sword')

        lines = [
            ('First name', 'Last name', 'Attack',        'Weapons'),
            ('Unchô',      'Kan-u',     'strangulation', 'spear'),
        ]

        doc = self._build_csv_doc(lines, user=user)
        url = self._build_import_url(FakeContact)

        def post():
            return self.client.post(
                url, follow=True,
                data={
                    **self.lv_import_data,
                    'document': doc.id,
                    'has_header': True,
                    'user': user.id,

                    f'custom_field-{cf_enum.id}_colselect': 3,
                    f'custom_field-{cf_enum.id}_create':    True,

                    f'custom_field-{cf_menum.id}_colselect': 4,
                    f'custom_field-{cf_menum.id}_create':    True,
                },
            )

        response1 = post()
        form1 = response1.context['form']
        self.assertFormError(
            form1, field=f'custom_field-{cf_enum.id}', errors='You can not create choices',
        )
        self.assertFormError(
            form1, field=f'custom_field-{cf_menum.id}', errors='You can not create choices',
        )

        # ---
        role = user.role
        role.admin_4_apps = ['creme_config']
        role.save()

        response = post()
        self.assertNoFormError(response)

        self._execute_job(response)
        self.get_object_or_fail(
            CustomFieldEnumValue, custom_field=cf_enum, value='strangulation',
        )
        self.get_object_or_fail(
            CustomFieldEnumValue, custom_field=cf_menum, value='spear',
        )

    def test_mass_import_customfields05(self):
        "Default value"
        user = self.login_as_root_and_get()
        contact_ids = [*FakeContact.objects.values_list('id', flat=True)]

        create_cf = partial(CustomField.objects.create, content_type=self.ct)
        cf_int  = create_cf(name='Size (cm)', field_type=CustomField.INT)
        cf_enum = create_cf(name='Attack',    field_type=CustomField.ENUM)
        cf_menum = create_cf(name='Weapons',  field_type=CustomField.MULTI_ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        punch = create_evalue(custom_field=cf_enum,  value='Punch')
        sword = create_evalue(custom_field=cf_menum, value='Sword')

        lines = [
            ('First name', 'Last name', 'Size', 'Attack', 'Weapons'),
            ('Unchô',      'Kan-u',   '',     '',       ''),
        ]

        doc = self._build_csv_doc(lines, user=user)
        url = self._build_import_url(FakeContact)

        def post(defint):
            return self.client.post(
                url, follow=True,
                data={
                    **self.lv_import_data,
                    'document': doc.id,
                    'has_header': True,
                    'user': user.id,
                    'key_fields': ['first_name', 'last_name'],

                    f'custom_field-{cf_int.id}_colselect': 3,
                    f'custom_field-{cf_int.id}_defval':    defint,

                    f'custom_field-{cf_enum.id}_colselect': 4,
                    f'custom_field-{cf_enum.id}_defval':    str(punch.id),

                    f'custom_field-{cf_menum.id}_colselect': 5,
                    f'custom_field-{cf_menum.id}_defval':    str(sword.id),
                },
            )

        response = post('notint')
        self.assertFormError(
            self.get_form_or_fail(response),
            field=f'custom_field-{cf_int.id}', errors=_('Enter a whole number.'),
        )

        response = post('180')
        self.assertNoFormError(response)

        self._execute_job(response)
        self.assertEqual(
            len(lines) - 1,
            FakeContact.objects.exclude(id__in=contact_ids).count(),
        )

        line = lines[1]
        kanu = self.get_object_or_fail(FakeContact, first_name=line[0], last_name=line[1])

        get_cf_values = self._get_cf_values
        self.assertEqual(180,   get_cf_values(cf_int,  kanu).value)
        self.assertEqual(punch, get_cf_values(cf_enum, kanu).value)
        self.assertListEqual([sword], [*get_cf_values(cf_menum, kanu).value.all()])

    def test_import_error01(self):
        "Form error: unknown extension."
        user = self.login_as_root_and_get()

        doc = self._build_doc(self._build_file(b'Non Empty File...', 'doc'), user=user)
        response = self.assertPOST200(
            self._build_import_url(FakeContact), data={'step': 0, 'document': doc.id},
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_(
                'Error reading document, unsupported file type: {file}.'
            ).format(file=doc.filedata.name),
        )

    def test_import_error02(self):
        "Validate default value."
        user = self.login_as_root_and_get()

        lines = [
            ('Name', 'Capital'),
            ('Nerv', '1000'),
        ]

        doc = self._build_csv_doc(lines, separator=';', user=user)
        url = self._build_import_url(FakeOrganisation)
        response = self.assertPOST200(
            url,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'has_header': True,
                'user': user.id,
                'name_colselect': 1,

                'capital_colselect': 2,
                'capital_defval': 'notint',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='capital', errors=_('Enter a whole number.'),
        )

    def test_import_error03(self):
        "Required field without column or default value."
        user = self.login_as_root_and_get()

        lines = [('Capital',), ('1000',)]  # No 'Name'
        doc = self._build_csv_doc(lines, separator=';', user=user)
        response = self.assertPOST200(
            self._build_import_url(FakeOrganisation),
            data={
                **self.lv_import_data,
                'document': doc.id,
                'has_header': True,
                'user': user.id,
                'name_colselect': 0,
                'capital_colselect': 1,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='name', errors=_('This field is required.'),
        )

    def test_import_error04(self):
        "Required custom-field without column or default value."
        user = self.login_as_root_and_get()

        create_cf = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeContact),
        )
        cf1 = create_cf(field_type=CustomField.STR, name='Dogtag')
        cf2 = create_cf(field_type=CustomField.INT, name='Eva number', is_required=True)

        lines = [('Ayanami', )]
        doc = self._build_csv_doc(lines, separator=';', user=user)
        response = self.assertPOST200(
            self._build_import_url(FakeContact),
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,

                f'custom_field-{cf1.id}_colselect': 0,

                f'custom_field-{cf2.id}_colselect': 0,
                # f'custom_field-{cf2.id}_defval': 1,
            },
        )
        form = self.get_form_or_fail(response)
        self.assertFormError(
            form,
            field=f'custom_field-{cf2.id}',
            errors=_('This field is required.'),
        )
        self.assertNotIn(f'custom_field-{cf1.id}', form.errors)

    @override_settings(MAX_JOBS_PER_USER=1)
    def test_import_error05(self):
        "Max jobs."
        user = self.login_as_root_and_get()
        Job.objects.create(
            user=user,
            type_id=mass_import_type.id,
            language='en',
            status=Job.STATUS_WAIT,
        )

        response = self.assertGET200(self._build_import_url(FakeContact), follow=True)
        self.assertRedirects(response, reverse('creme_core__my_jobs'))

    def test_auxiliary_creation(self):
        """Ok if several fields but the not selected fields have a default value."""
        user = self.login_as_root_and_get()

        priority = FakeTicketPriority.objects.first()

        ticket_title = 'Duplicated ticket'
        status_name = 'Duplicated'
        doc = self._build_csv_doc([(ticket_title, status_name)], user=user)
        response = self.assertPOST200(
            self._build_import_url(FakeTicket),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'title_colselect': 1,

                'priority_colselect': 0,
                'priority_defval': priority.id,

                'status_colselect': 2,
                'status_subfield': 'name',
                'status_create': True,
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        ticket = self.get_object_or_fail(FakeTicket, title=ticket_title)
        self.assertEqual(priority, ticket.priority)

        status = self.get_object_or_fail(FakeTicketStatus, name=status_name)
        self.assertEqual(status, ticket.status)
        self.assertEqual('FF0000', status.color)

    def test_auxiliary_creation_error01(self):
        "Creation for 'auxiliary' model is disabled in creme_config."
        user = self.login_as_root_and_get()

        doc = self._build_csv_doc([('Ayanami', 'Rei', 'Pilot')], user=user)
        response = self.assertPOST200(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'first_name_colselect': 2,
                'last_name_colselect': 1,

                'position_colselect': 3,
                'position_subfield': 'title',
                'position_create': True,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='position', errors='You can not create instances',
        )

    def test_auxiliary_creation_error02(self):
        "Creation for 'auxiliary' model in creme_config use a custom URL."
        user = self.login_as_root_and_get()

        doc = self._build_csv_doc([('NERV', 'Secret organisation')], user=user)
        response = self.assertPOST200(
            self._build_import_url(FakeOrganisation),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'name_colselect': 1,

                'legal_form_colselect': 2,
                'legal_form_subfield': 'title',
                'legal_form_create': True,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='legal_form', errors='You can not create instances',
        )

    def test_auxiliary_creation_error03(self):
        "Several fields, only one without a default value but another one is selected."
        user = self.login_as_root_and_get()
        priority = FakeTicketPriority.objects.first()
        doc = self._build_csv_doc([('Duplicated ticket', '00ff00')], user=user)
        response = self.assertPOST200(
            self._build_import_url(FakeTicket),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'title_colselect': 1,

                'priority_colselect': 0,
                'priority_defval': priority.id,

                'status_colselect': 2,
                'status_subfield': 'color',
                'status_create': True,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='status',
            errors=_(
                'You can not create a «{model}» with only a value for «{field}»'
            ).format(model='Test Ticket status', field=_('Color')),
        )

    def test_credentials01(self):
        "Creation credentials for imported model."
        user = self.login_as_standard(
            allowed_apps=['creme_core'],
            creatable_models=[FakeOrganisation],  # Not Contact
        )
        self.assertFalse(user.has_perm_to_create(FakeContact))
        self.assertGET403(self._build_import_url(FakeContact))

    def test_credentials02(self):
        "Creation credentials for 'auxiliary' models."
        user = self.login_as_standard(
            allowed_apps=['creme_core', 'documents'],
            creatable_models=[FakeContact, FakeOrganisation, Document],
        )
        self.add_credentials(user.role, own='*')

        doc = self._build_csv_doc([('Ayanami', 'Rei', 'Piloting')], user=user)
        response = self.assertPOST200(
            self._build_import_url(FakeContact),
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'first_name_colselect': 2,
                'last_name_colselect': 1,

                'sector_colselect': 3,
                'sector_subfield': 'title',
                'sector_create': True,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='sector', errors='You can not create instances',
        )

    def test_credentials03(self):
        "Creation credentials for related entities."
        user = self.login_as_standard(
            allowed_apps=['creme_core', 'documents'],
            creatable_models=[FakeContact, Document],  # Not Organisation
        )
        self.add_credentials(user.role, own='*')

        employed = RelationType.objects.builder(
            id='test-subject_employed_by', predicate='is an employee of',
        ).symmetric(id='test-object_employed_by', predicate='employs').get_or_create()[0]
        doc = self._build_csv_doc([('Ayanami', 'Rei', 'NERV')], user=user)
        response = self.assertPOST200(
            self._build_import_url(FakeContact),
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'first_name_colselect': 2,
                'last_name_colselect': 1,

                'dyn_relations': self._dyn_relations_value(employed, FakeOrganisation, 3, 'name'),
                'dyn_relations_can_create': True,
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='dyn_relations',
            errors=_(
                'You are not allowed to create: %(model)s'
            ) % {'model': 'Test Organisation'},
        )

    def test_import_with_update01(self):
        user = self.login_as_root_and_get()

        create_contact = partial(FakeContact.objects.create, user=user)
        shinji = create_contact(first_name='Shinji', last_name='Ikari')
        gendo  = create_contact(first_name='Gendo',  last_name='Ikari')

        loves = RelationType.objects.builder(
            id='test-subject_loving', predicate='is loving',
        ).symmetric(id='test-object_loving', predicate='is loved by').get_or_create()[0]

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='Really cute in her suit')
        ptype2 = create_ptype(text='Has blue hairs')

        rei_info = {
            'first_name': 'Rei',   'last_name': 'Ayanami', 'phone': '111111', 'email': '\t ',
        }
        asuka_info = {
            'first_name': 'Asuka', 'last_name': 'Langley', 'phone': '222222', 'email': '',
        }

        rei_mobile = '54554'
        rei_email = 'rei.ayanami@nerv.jp'
        rei = FakeContact.objects.get_or_create(
            first_name=rei_info['first_name'],
            last_name=rei_info['last_name'],
            defaults={'user': user},
        )[0]
        self.assertNotEqual(rei_info['phone'], rei.phone)

        update_model_instance(rei, mobile=rei_mobile, email=rei_email)

        # This relation & this property should not be duplicated
        Relation.objects.create(subject_entity=rei, type=loves, object_entity=shinji, user=user)
        CremeProperty.objects.create(type=ptype1, creme_entity=rei)

        # Should not be modified, even is 'first_name' is searched
        rei2 = FakeContact.objects.get_or_create(
            first_name=rei_info['first_name'],
            last_name='Iyanima',
            defaults={'user': user},
        )[0]

        self.assertFalse(FakeContact.objects.filter(last_name=asuka_info['last_name']))

        count = FakeContact.objects.count()
        doc = self._build_csv_doc(
            [
                (d['first_name'], d['last_name'], d['phone'], d['email'])
                for d in (rei_info, asuka_info)
            ],
            user=user,
        )
        response = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'key_fields': ['first_name', 'last_name'],
                'phone_colselect': 3,
                'email_colselect': 4,
                'property_types': [ptype1.id, ptype2.id],
                'fixed_relations': self.formfield_value_multi_relation_entity(
                    (loves, shinji),
                    (loves, gendo),
                ),
            },
        )
        self.assertNoFormError(response)
        job = self._execute_job(response)

        self.assertEqual(count + 1, FakeContact.objects.count())

        rei = self.refresh(rei)
        self.assertEqual(rei_info['phone'], rei.phone)
        self.assertEqual(rei_mobile,        rei.mobile)  # Value not erased (no column)
        self.assertEqual(rei_email,         rei.email)   # Value not erased (empty cell)
        self.assertHaveRelation(subject=rei, type=loves, object=gendo)
        self.assertHaveRelation(subject=rei, type=loves, object=shinji)  # <== not IntegrityError
        self.assertHasProperty(entity=rei, ptype=ptype2)
        self.assertHasProperty(entity=rei, ptype=ptype1)  # <= no IntegrityError (2 prop) !

        self.assertIsNone(self.refresh(rei2).phone)

        # TODO: if FakeContact.email.null == False
        # asuka = self.get_object_or_fail(FakeContact, **asuka_info)
        asuka = self.get_object_or_fail(
            FakeContact,
            first_name=asuka_info['first_name'],
            last_name=asuka_info['last_name'],
        )
        self.assertEqual(asuka.phone, asuka_info['phone'])
        self.assertFalse(asuka.email)

        jresult = self.get_object_or_fail(MassImportJobResult, job=job, entity=asuka)
        self.assertFalse(jresult.updated)

        jresult = self.get_object_or_fail(MassImportJobResult, job=job, entity=rei)
        self.assertTrue(jresult.updated)

        self.assertListEqual(
            [
                ngettext(
                    '{count} «{model}» has been created.',
                    '{count} «{model}» have been created.',
                    1
                ).format(count=1, model='Test Contact'),
                ngettext(
                    '{count} «{model}» has been updated.',
                    '{count} «{model}» have been updated.',
                    1
                ).format(count=1, model='Test Contact'),
                ngettext(
                    '{count} line in the file.',
                    '{count} lines in the file.',
                    2
                ).format(count=2),
            ],
            job.stats
        )

    def test_import_with_update02(self):
        "Several existing entities found."
        user = self.login_as_root_and_get()

        last_name = 'Ayanami'
        first_name = 'Rei'

        create_contact = partial(
            FakeContact.objects.get_or_create, user=user, last_name=last_name,
        )
        create_contact(first_name='Lei')
        create_contact(first_name='Rey')

        count = FakeContact.objects.count()

        doc = self._build_csv_doc([(last_name, first_name)], user=user)
        response = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'key_fields': ['last_name'],
                'last_name_colselect': 1,
                'first_name_colselect': 2,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        self.assertEqual(count + 1, FakeContact.objects.count())
        rei = self.get_object_or_fail(FakeContact, last_name=last_name, first_name=first_name)

        jr_error = self.get_alone_element(self._get_job_results(job))
        self.assertEqual([last_name, first_name], jr_error.line)
        self.assertListEqual(
            [
                _(
                    'Several entities corresponding to the search have been found. '
                    'So a new entity have been created to avoid errors.'
                )
            ],
            jr_error.messages,
        )

        self.assertEqual(rei, jr_error.entity.get_real_entity())

    def test_import_with_update03(self):
        "Ignore trashed entities."
        user = self.login_as_root_and_get()

        last_name = 'Ayanami'
        first_name = 'Rei'

        c = FakeContact.objects.create(user=user, last_name=last_name, first_name='Lei')
        c.trash()

        count = FakeContact.objects.count()

        doc = self._build_csv_doc([(last_name, first_name)], user=user)
        response = self.client.post(
            self._build_import_url(FakeContact), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'key_fields': ['last_name'],
                'last_name_colselect': 1,
                'first_name_colselect': 2,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        self.assertEqual(count + 1, FakeContact.objects.count())
        self.get_object_or_fail(FakeContact, last_name=last_name, first_name=first_name)

        results = self._get_job_results(job)
        self.assertEqual(1, len(results))

    def test_import_with_update04(self):
        "Ignore non editable entities."
        user = self.login_as_standard(
            allowed_apps=['creme_core', 'documents'],
            creatable_models=[FakeContact, Document],
        )
        self.add_credentials(user.role, own='*')
        self.add_credentials(user.role, all='!CHANGE', model=FakeContact)

        last_name = 'Ayanami'
        first_name = 'Rei'

        c = FakeContact.objects.create(
            user=self.get_root_user(), last_name=last_name, first_name='Lei',
        )
        self.assertTrue(user.has_perm_to_view(c))
        self.assertFalse(user.has_perm_to_change(c))

        count = FakeContact.objects.count()

        doc = self._build_csv_doc([(last_name, first_name)], user=user)
        response = self.client.post(
            self._build_import_url(FakeContact), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'key_fields': ['last_name'],
                'last_name_colselect': 1,
                'first_name_colselect': 2,
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)

        self.assertEqual(count + 1, FakeContact.objects.count())
        self.get_object_or_fail(FakeContact, last_name=last_name, first_name=first_name)

        results = self._get_job_results(job)
        self.assertEqual(1, len(results))

    def test_import_with_update05(self):
        "Update key uses a FK."
        user = self.login_as_root_and_get()

        civ1, civ2 = FakeCivility.objects.all()[:2]

        last_name = 'Ayanami'
        create_contact = partial(FakeContact.objects.create, user=user, last_name=last_name)
        contact1 = create_contact(civility=civ1)
        contact2 = create_contact(civility=civ2)

        count = FakeContact.objects.count()

        email = 'ayanami@nerv.jp'

        url = self._build_import_url(FakeContact)
        doc = self._build_csv_doc([(last_name, civ2.title, email)], user=user)

        # Check key fields
        response = self.client.post(url, data={'step': 0, 'document': doc.id})
        self.assertNoFormError(response)

        with self.assertNoException():
            key_choices = response.context['form'].fields['key_fields'].choices

        self.assertInChoices(value='civility', label=_('Civility'), choices=key_choices)
        self.assertNotInChoices(value='civility__title',    choices=key_choices)
        self.assertNotInChoices(value='civility__shortcut', choices=key_choices)
        self.assertNotInChoices(value='address',            choices=key_choices)  # Not enumerable
        self.assertNotInChoices(value='address__city',      choices=key_choices)  # Idem
        self.assertNotInChoices(value='languages',          choices=key_choices)  # M2M

        # Final POST
        response = self.client.post(
            url,
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'key_fields': ['last_name', 'civility'],

                'first_name_colselect': 0,
                'last_name_colselect': 1,

                'civility_colselect': 2,
                'civility_subfield': 'title',

                'email_colselect': 3,
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        self.assertEqual(count, FakeContact.objects.count())

        self.assertFalse(self.refresh(contact1).email)
        self.assertEqual(email, self.refresh(contact2).email)

    def test_validate_subfield(self):
        user = self.login_as_root_and_get()

        doc = self._build_csv_doc([('Rei', 'Ayanami', 'Pilot')], user=user)
        response = self.assertPOST200(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,

                'position_colselect': 3,
                'position_subfield': 'invalid',  # <=

                'phone_subfield': 'wtf',  # <= should not crash...
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='position',
            errors=_(
                'Select a valid choice. "{value}" is not one of the available sub-field.'
            ).format(value='invalid'),
        )

    def test_fields_config_hidden(self):
        user = self.login_as_root_and_get()

        hidden_fname1 = 'phone'
        hidden_fname2 = 'description'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (hidden_fname1, {FieldsConfig.HIDDEN: True}),
                (hidden_fname2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        rei_info = {
            'first_name': 'Rei', 'last_name': 'Ayanami',
            hidden_fname1: '111111', 'email': 'rei.ayanami@nerv.jp',
        }
        doc = self._build_csv_doc(
            [(
                rei_info['first_name'], rei_info['last_name'],
                rei_info['phone'], rei_info['email'],
            )],
            user=user,
        )
        url = self._build_import_url(FakeContact)
        response = self.client.post(url, data={'step': 0, 'document': doc.id})
        self.assertNoFormError(response)

        with self.assertNoException():
            fields = response.context['form'].fields
            key_choices = fields['key_fields'].choices

        self.assertInChoices(value='last_name', label=_('Last name'), choices=key_choices)
        self.assertNotInChoices(value=hidden_fname1, choices=key_choices)
        self.assertNotInChoices(value=hidden_fname2, choices=key_choices)

        self.assertIn('last_name', fields)
        self.assertNotIn(hidden_fname1, fields)

        response = self.client.post(
            url,
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'key_fields': ['first_name', 'last_name'],
                'phone_colselect': 3,  # Should be ignored
                'email_colselect': 4,
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        rei = self.get_object_or_fail(
            FakeContact,
            last_name=rei_info['last_name'], first_name=rei_info['first_name'],
        )
        self.assertEqual(rei_info['email'], rei.email)
        self.assertIsNone(getattr(rei, hidden_fname1))

    def test_fields_config_required(self):
        user = self.login_as_root_and_get()

        required_fname = 'phone'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(required_fname, {FieldsConfig.REQUIRED: True})],
        )

        info = [
            {'first_name': 'Rei',   'last_name': 'Ayanami', required_fname: '111111'},
            {'first_name': 'Asuka', 'last_name': 'Langley', required_fname: ''},
        ]
        doc = self._build_csv_doc(
            [
                (c_info['first_name'], c_info['last_name'], c_info[required_fname])
                for c_info in info
            ],
            user=user,
        )

        url = self._build_import_url(FakeContact)
        data = {
            **self.lv_import_data,
            'document': doc.id,
            'user': user.id,
        }
        response1 = self.client.post(url, follow=True, data=data)
        self.assertFormError(
            response1.context['form'],
            field=required_fname, errors=_('This field is required.'),
        )

        # ---
        data[f'{required_fname}_colselect'] = 3
        response2 = self.client.post(url, follow=True, data=data)
        self.assertNoFormError(response2)

        job = self._get_job(response2)
        mass_import_type.execute(job)

        rei_info = info[0]
        self.get_object_or_fail(
            FakeContact,
            last_name=rei_info['last_name'],
            first_name=rei_info['first_name'],
            **{required_fname: rei_info[required_fname]}
        )

        jresults = MassImportJobResult.objects.filter(job=job)
        self.assertEqual(2, len(jresults))

        jr_error = self.get_alone_element(r for r in jresults if r.messages)
        self.assertIsNone(jr_error.entity_ctype)
        self.assertIsNone(jr_error.entity)
        self.assertListEqual(
            [_('The field «{}» has been configured as required.').format(_('Phone'))],
            jr_error.messages,
        )

    def test_resume(self):
        user = self.login_as_root_and_get()
        lines = [
            ('Rei',   'Ayanami'),
            ('Asuka', 'Langley'),
        ]

        rei_line = lines[0]
        rei = FakeContact.objects.create(
            user=user, first_name=rei_line[0], last_name=rei_line[1],
        )

        count = FakeContact.objects.count()
        doc = self._build_csv_doc(lines, user=user)
        response = self.client.post(
            self._build_import_url(FakeContact), follow=True,
            data={**self.lv_import_data, 'document': doc.id, 'user': user.id},
        )
        self.assertNoFormError(response)

        job = self._get_job(response)
        # We simulate an interrupted job
        MassImportJobResult.objects.create(job=job, real_entity=rei)

        mass_import_type.execute(job)
        self.assertEqual(count + 1, FakeContact.objects.count())

        asuka_line = lines[1]
        self.get_object_or_fail(FakeContact, first_name=asuka_line[0], last_name=asuka_line[1])

    def _aux_test_dl_errors(self, doc_builder, result_builder, ext, header=False):
        "CSV, no header."
        user = self.login_as_root_and_get()

        first_name = 'Unchô'
        last_name = 'Kan-u'
        birthday = '1995'
        lines = [('First name',   'Last name', 'Birthday')] if header else []
        lines.append((first_name, last_name,   birthday))  # Error
        lines.append(('Asuka',    'Langley',   self.formfield_value_date(1997, 2, 1)))  # OK

        doc = doc_builder(lines, user=user)
        data = {
            **self.lv_import_data,
            'document': doc.id,
            'user': user.id,
            'birthday_colselect': 3,
        }

        if header:
            data['has_header'] = 'on'

        response = self.client.post(
            self._build_import_url(FakeContact), follow=True, data=data,
        )
        self.assertNoFormError(response)
        job = self._execute_job(response)

        jresults = MassImportJobResult.objects.filter(job=job)
        self.assertEqual(2, len(jresults))
        self.assertIsNone(jresults[1].messages)

        j_error = jresults[0]
        kanu = j_error.entity
        self.assertIsNotNone(kanu)
        self.assertEqual(first_name, kanu.get_real_entity().first_name)
        self.assertListEqual([_('Enter a valid date.')], j_error.messages)

        response = self.assertGET200(self._build_dl_errors_url(job), follow=True)

        cdisp = response['Content-Disposition']
        self.assertStartsWith(cdisp, f'attachment; filename="{slugify(doc.title)}-errors')
        self.assertEndsWith(cdisp, f'.{ext}"')

        result_lines = [['First name',   'Last name', 'Birthday', _('Errors')]] if header else []
        result_lines.append([first_name, last_name,   birthday,   _('Enter a valid date.')])

        self.assertEqual(result_lines, result_builder(response))

    @staticmethod
    def _csv_to_list(response):
        separator = ','

        return [
            [i[1:-1] for i in line.split(separator)]
            for line in smart_str(response.content).splitlines()
        ]

    def test_dl_errors01(self):
        "CSV, no header."
        self._aux_test_dl_errors(
            self._build_csv_doc,
            result_builder=self._csv_to_list,
            ext='csv',
            header=False,
        )

    def test_dl_errors02(self):
        "CSV, header."  # TODO: other separator
        self._aux_test_dl_errors(
            self._build_csv_doc,
            result_builder=self._csv_to_list,
            ext='csv',
            header=True,
        )

    def test_dl_errors03(self):
        "XLS."
        def result_builder(response):
            return [*XlrdReader(None, file_contents=b''.join(response.streaming_content))]

        self._aux_test_dl_errors(
            self._build_xls_doc,
            result_builder=result_builder,
            ext='xls',
            header=True,
            # follow=True,
        )

    def test_dl_errors04(self):
        "Bad Job type."
        user = self.login_as_root_and_get()
        job = Job.objects.create(
            user=user,
            type_id=batch_process_type.id,
            language='en',
            status=Job.STATUS_WAIT,
            # raw_data='',
        )

        self.assertGET404(self._build_dl_errors_url(job))

    def test_dl_errors05(self):
        "Bad user."
        self.login_as_standard()
        job = Job.objects.create(
            user=self.get_root_user(),
            type_id=mass_import_type.id,
            language='en',
            status=Job.STATUS_WAIT,
            # raw_data='',
        )

        self.assertGET403(self._build_dl_errors_url(job))
