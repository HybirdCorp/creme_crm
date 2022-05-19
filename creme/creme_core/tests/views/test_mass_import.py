# -*- coding: utf-8 -*-

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

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.bricks import JobErrorsBrick, MassImportJobErrorsBrick
from creme.creme_core.creme_jobs import batch_process_type, mass_import_type
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
    FieldsConfig,
    Job,
    MassImportJobResult,
    Relation,
    RelationType,
    SetCredentials,
)
from creme.creme_core.utils import update_model_instance
from creme.creme_core.utils.xlrd_utils import XlrdReader
from creme.documents.models import Document
from creme.documents.tests.base import skipIfCustomDocument, skipIfCustomFolder

from .base import (
    BrickTestCaseMixin,
    MassImportBaseTestCaseMixin,
    ViewsTestCase,
)


@skipIfCustomDocument
@skipIfCustomFolder
class MassImportViewsTestCase(MassImportBaseTestCaseMixin,
                              BrickTestCaseMixin,
                              ViewsTestCase):
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
        user = self.login()

        count = FakeContact.objects.count()
        lines = [
            ('Rei',   'Ayanami'),
            ('Asuka', 'Langley'),
        ]

        doc = builder(lines)
        url = self._build_import_url(FakeContact)
        response = self.assertGET200(url)

        with self.assertNoException():
            response.context['form']  # NOQA

        response = self.client.post(
            url,
            data={
                'step':     0,
                'document': doc.id,
                # has_header
            },
        )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        self.assertIn('value="1"', str(form['step']))

        response = self.client.post(
            url,
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
            },
        )
        self.assertNoFormError(response)

        jobs = Job.objects.all()
        self.assertEqual(1, len(jobs))

        job = jobs[0]
        self.assertEqual(self.user, job.user)
        self.assertIsNone(job.last_run)
        self.assertIsInstance(job.data, dict)
        self.assertEqual(Job.STATUS_WAIT, job.status)
        self.assertIsNone(job.error)
        self.assertFalse(self._get_job_results(job))

        # Properties
        self.assertIs(mass_import_type, job.type)
        self.assertListEqual(
            [_('Import «{model}» from {doc}').format(model='Test Contact', doc=doc)],
            job.description
        )  # TODO: description of columns ????

        self.assertRedirects(response, job.get_absolute_url())

        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, MassImportJobErrorsBrick.id_)

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
        self.assertSetEqual({*contacts}, {r.entity.get_real_entity() for r in results})
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

        # Reload brick -----------
        reload_url = reverse('creme_core__reload_job_bricks', args=(job.id,))
        brick_id = MassImportJobErrorsBrick.id_
        response = self.assertGET200(reload_url, data={'brick_id': brick_id})

        with self.assertNoException():
            results = response.json()

        self.assertIsList(results, length=1)

        result = results[0]
        self.assertIsList(result, length=2)
        self.assertEqual(brick_id, result[0])

        tree = self.get_html_tree(result[1])
        self.get_brick_node(tree, brick_id)

        self.assertGET404(reload_url, data={'brick_id': JobErrorsBrick.id_})

    def _test_import02(self, builder):
        """Use header, default value, model search and create, properties,
        fixed and dynamic relations.
        """
        user = self.login()

        pos_title  = 'Pilot'
        sctr_title = 'Army'
        self.assertFalse(FakePosition.objects.filter(title=pos_title).exists())
        self.assertFalse(FakeSector.objects.filter(title=sctr_title).exists())

        position_ids = [*FakePosition.objects.values_list('id', flat=True)]
        sector_ids   = [*FakeSector.objects.values_list('id', flat=True)]

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(
            str_pk='test-prop_cute', text='Really cute in her suit',
        )
        ptype2 = create_ptype(
            str_pk='test-prop_accurate', text='Great accuracy',
            subject_ctypes=[FakeContact],
        )
        ptype3 = create_ptype(
            str_pk='test-prop_international', text='International',
            subject_ctypes=[FakeOrganisation],
        )

        ptype4 = create_ptype(str_pk='test-prop_disabled', text='Disabled')
        ptype4.enabled = False
        ptype4.save()

        create_rtype = RelationType.objects.smart_update_or_create
        employed = create_rtype(
            ('persons-subject_employed_by', 'is an employee of'),
            ('persons-object_employed_by',  'employs'),
        )[0]
        loves = create_rtype(
            ('test-subject_loving', 'is loving'),
            ('test-object_loving',  'is loved by'),
        )[0]

        nerv = FakeOrganisation.objects.create(user=self.user, name='Nerv')
        shinji = FakeContact.objects.create(user=self.user, first_name='Shinji', last_name='Ikari')
        contact_count = FakeContact.objects.count()

        city = 'Tokyo'
        lines = [
            ('First name', 'Last name', 'Position', 'Sector',   'City', 'Organisation'),
            ('Rei',        'Ayanami',   pos_title,  sctr_title, city,   nerv.name),
            ('Asuka',      'Langley',   pos_title,  sctr_title, '',     ''),
        ]

        doc = builder(lines)
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

        self.assertIn('value="1"',    str(form['step']))
        self.assertIn('value="True"', str(form['has_header']))

        self.assertInChoices(value=ptype1.id, label=ptype1.text, choices=properties_choices)
        self.assertInChoices(value=ptype2.id, label=ptype2.text, choices=properties_choices)
        self.assertNotInChoices(value=ptype3.id, choices=properties_choices)
        self.assertNotInChoices(value=ptype4.id, choices=properties_choices)

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
                'position_create': True,

                'sector_colselect': 4,
                'sector_subfield': 'title',
                'sector_defval': '',  # The browser POST an empty string
                # sector_create=False,

                'property_types': [ptype1.id],

                'fixed_relations': self.formfield_value_multi_relation_entity(
                    [loves.id, shinji]
                ),
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

        positions = FakePosition.objects.exclude(id__in=position_ids)
        self.assertEqual(1, len(positions))

        position = positions[0]
        self.assertEqual(pos_title, position.title)

        self.assertFalse(FakeSector.objects.exclude(id__in=sector_ids).exists())

        created_contacts = {}
        for first_name, last_name, pos_title, sector_title, city_name, __orga_name in lines[1:]:
            contact = self.get_object_or_fail(
                FakeContact, first_name=first_name, last_name=last_name,
            )
            created_contacts[first_name] = contact

            self.assertEqual(default_descr, contact.description)
            self.assertEqual(position,      contact.position)
            self.get_object_or_fail(CremeProperty, type=ptype1, creme_entity=contact.id)
            self.assertRelationCount(1, contact, loves.id, shinji)

        self.assertRelationCount(1, created_contacts['Rei'],   employed.id, nerv)
        self.assertRelationCount(0, created_contacts['Asuka'], employed.id, nerv)

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
        "Create entities to link with them"
        user = self.login()
        contact_ids = [*FakeContact.objects.values_list('id', flat=True)]

        orga_name = 'Nerv'
        self.assertFalse(FakeOrganisation.objects.filter(name=orga_name))

        employed = RelationType.objects.smart_update_or_create(
            ('test-subject_employed_by', 'is an employee of'),
            ('test-object_employed_by',  'employs'),
        )[0]
        doc = builder([('Ayanami', 'Rei', orga_name)])
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

        contacts = FakeContact.objects.exclude(id__in=contact_ids)
        self.assertEqual(1, len(contacts))

        rei = contacts[0]
        relations = Relation.objects.filter(subject_entity=rei, type=employed)
        self.assertEqual(1, len(relations))

        employer = relations[0].object_entity.get_real_entity()
        self.assertIsInstance(employer, FakeOrganisation)
        self.assertEqual(orga_name, employer.name)

        results = self._get_job_results(job)
        self.assertEqual(1, len(results))
        self.assertFalse(results[0].messages)

    def test_not_registered(self):
        self.login()
        self.assertGET404(self._build_import_url(FakeEmailCampaign))

    def test_mass_import01(self):
        return self._test_import01(self._build_csv_doc)

    def test_mass_import02(self):
        return self._test_import02(self._build_csv_doc)

    def test_mass_import03(self):
        return self._test_import03(self._build_csv_doc)

    def test_xls_import01(self):
        return self._test_import01(self._build_xls_doc)

    def test_xls_import02(self):
        return self._test_import02(self._build_xls_doc)

    def test_xls_import03(self):
        return self._test_import03(self._build_xls_doc)

    def test_mass_import04(self):
        "Other separator"
        user = self.login()
        contact_ids = [*FakeContact.objects.values_list('id', flat=True)]

        lines = [
            ('First name', 'Last name'),
            ('Unchô',      'Kan-u'),
            ('Gentoku',    'Ryûbi'),
        ]

        doc = self._build_csv_doc(lines, separator=';')
        url = self._build_import_url(FakeContact)
        response = self.client.post(
            url,
            data={
                'step':     0,
                'document': doc.id,
            },
        )
        self.assertNoFormError(response)
        self.assertIn('value="1"', str(response.context['form']['step']))

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

    def test_duplicated_relations(self):
        "Same Relation in fixed & dynamic fields at creation."
        user = self.login()

        employed = RelationType.objects.smart_update_or_create(
            ('test-subject_employed_by', 'employed by'),
            ('test-object_employed_by',  'employs'),
        )[0]

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name)])
        response = self.client.post(
            self._build_import_url(FakeContact), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'fixed_relations': self.formfield_value_multi_relation_entity(
                    [employed.id, nerv],
                ),
                'dyn_relations': self._dyn_relations_value(
                    employed, FakeOrganisation, 3, 'name',
                ),
            },
        )

        self._execute_job(response)

        rei = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertRelationCount(1, rei, employed.id, nerv)  # Not 2

    def test_relations_with_property_constraint01(self):
        "Constraint on object."
        user = self.login()

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_rich', text='Is rich',
        )
        employed = RelationType.objects.smart_update_or_create(
            ('test-subject_employed_by', 'employed by', [FakeContact]),
            ('test-object_employed_by',  'employs',     [FakeOrganisation], [ptype]),
        )[0]

        create_orga = partial(FakeOrganisation.objects.create, user=user)
        nerv = create_orga(name='Nerv')  # No ptype

        seele = create_orga(name='Seele')
        CremeProperty.objects.create(type=ptype, creme_entity=seele)

        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name, seele.name)])

        # Fixed relation
        response1 = self.client.post(
            self._build_import_url(FakeContact), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'fixed_relations': self.formfield_value_multi_relation_entity(
                    [employed.id, nerv],
                    [employed.id, seele],
                ),
            },
        )
        self.assertFormError(
            response1, 'form', 'fixed_relations',
            _(
                'This entity has no property that matches the constraints of '
                'the type of relationship.'
            ),
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
        self.assertRelationCount(1, rei, employed.id, seele)
        self.assertRelationCount(0, rei, employed.id, nerv)

        results = self._get_job_results(job)
        self.assertEqual(1, len(results))
        self.assertListEqual(
            [
                _(
                    'The entity «{entity}» has no property «{property}» which is '
                    'mandatory for the relationship «{predicate}»'
                ).format(
                    entity=nerv,
                    property=ptype.text,
                    predicate=employed.predicate,
                ),
            ],
            results[0].messages,
        )

    def test_relations_with_property_constraint02(self):
        "Constraint on subject: fixed relationships + error."
        user = self.login()

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_pilot', text='Is a pilot',
        )
        employed = RelationType.objects.smart_update_or_create(
            ('test-subject_employed_by', 'employed by', [FakeContact], [ptype]),
            ('test-object_employed_by',  'employs',     [FakeOrganisation]),
        )[0]

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')  # No ptype

        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name)])

        response = self.client.post(
            self._build_import_url(FakeContact), follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'fixed_relations': self.formfield_value_multi_relation_entity(
                    [employed.id, nerv],
                ),
            },
        )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        rei = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertRelationCount(0, rei, employed.id, nerv)

        results = self._get_job_results(job)
        self.assertEqual(1, len(results))
        self.assertListEqual(
            [
                _(
                    'The entity has no property «{property}» which is '
                    'mandatory for the relationship «{predicate}»'
                ).format(
                    property=ptype.text,
                    predicate=employed.predicate,
                ),
            ],
            results[0].messages,
        )

    def test_relations_with_property_constraint03(self):
        "Constraint on subject: fixed relationships (OK)."
        user = self.login()

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_pilot', text='Is a pilot',
        )
        employed = RelationType.objects.smart_update_or_create(
            ('test-subject_employed_by', 'employed by', [FakeContact], [ptype]),
            ('test-object_employed_by',  'employs',     [FakeOrganisation]),
        )[0]

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name)])

        response = self.client.post(
            self._build_import_url(FakeContact),
            follow=True,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,
                'property_types': [ptype.id],
                'fixed_relations': self.formfield_value_multi_relation_entity(
                    [employed.id, nerv],
                ),
            },
        )
        self.assertNoFormError(response)

        self._execute_job(response)
        rei = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
        self.assertRelationCount(1, rei, employed.id, nerv)

    def test_relations_with_property_constraint04(self):
        "Constraint on subject: dynamic relationships + error."
        user = self.login()

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_pilot', text='Is a pilot',
        )
        employed = RelationType.objects.smart_update_or_create(
            ('test-subject_employed_by', 'employed by', [FakeContact], [ptype]),
            ('test-object_employed_by',  'employs',     [FakeOrganisation]),
        )[0]

        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name)])

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
        self.assertRelationCount(0, rei, employed.id, nerv)

        results = self._get_job_results(job)
        self.assertEqual(1, len(results))
        self.assertListEqual(
            [
                _(
                    'The entity has no property «{property}» which is '
                    'mandatory for the relationship «{predicate}»'
                ).format(
                    property=ptype.text,
                    predicate=employed.predicate,
                ),
            ],
            results[0].messages,
        )

    def test_relations_with_property_constraint05(self):
        "Constraint on subject: dynamic relationships (OK)."
        user = self.login()

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='test-prop_pilot', text='Is a pilot',
        )
        employed = RelationType.objects.smart_update_or_create(
            ('test-subject_employed_by', 'employed by', [FakeContact], [ptype]),
            ('test-object_employed_by',  'employs',     [FakeOrganisation]),
        )[0]
        nerv = FakeOrganisation.objects.create(user=user, name='Nerv')

        last_name = 'Ayanami'
        first_name = 'Rei'
        doc = self._build_csv_doc([(first_name, last_name, nerv.name)])
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
        self.assertRelationCount(1, rei, employed.id, nerv)

    def test_default_value(self):
        "Use default value when CSV value is empty (+ fix unicode bug)."
        user = self.login()

        first_name = 'Gentoku'
        last_name = 'Ryûbi'
        doc = self._build_csv_doc([(first_name, '')])
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
        user = self.login()

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

        doc = self._build_csv_doc(lines)
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

        jr_errors = [r for r in results if r.messages]
        self.assertEqual(1, len(jr_errors))

        jr_error = jr_errors[0]
        self.assertEqual([*lines[4]], jr_error.line)
        self.assertListEqual(
            [_('Enter a whole number.')],  # TODO: add the field verbose name !!
            jr_error.messages,
        )
        self.assertEqual(ryomou, jr_error.entity.get_real_entity())

    def test_mass_import_customfields02(self):
        "CustomField.ENUM/MULTI_ENUM (no creation of choice)."
        user = self.login()
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

        doc = self._build_csv_doc(lines)
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

        jr_errors = [r for r in results if r.messages]
        self.assertEqual(1, len(jr_errors))

        jr_error = jr_errors[0]
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
        user = self.login()
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

        doc = self._build_csv_doc(lines)
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
        user = self.login(
            is_superuser=False,
            allowed_apps=['creme_core', 'documents'],
            creatable_models=[FakeContact, Document],
        )

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

        doc = self._build_csv_doc(lines)
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

        response = post()
        self.assertFormError(
            response, 'form', f'custom_field-{cf_enum.id}', 'You can not create choices',
        )
        self.assertFormError(
            response, 'form', f'custom_field-{cf_menum.id}', 'You can not create choices',
        )

        role = self.role
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
        user = self.login()
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

        doc = self._build_csv_doc(lines)
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
            response, 'form', f'custom_field-{cf_int.id}', _('Enter a whole number.')
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
        "Form error: unknown extension"
        self.login()

        doc = self._build_doc(self._build_file(b'Non Empty File...', 'doc'))
        response = self.assertPOST200(
            self._build_import_url(FakeContact), data={'step': 0, 'document': doc.id},
        )
        self.assertFormError(
            response, 'form', None,
            _('Error reading document, unsupported file type: {file}.').format(
                file=doc.filedata.name,
            ),
        )

    def test_import_error02(self):
        "Validate default value"
        self.login()

        lines = [
            ('Name', 'Capital'),
            ('Nerv', '1000'),
        ]

        doc = self._build_csv_doc(lines, separator=';')
        url = self._build_import_url(FakeOrganisation)
        response = self.assertPOST200(
            url,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'has_header': True,
                'user': self.user.id,
                'name_colselect': 1,

                'capital_colselect': 2,
                'capital_defval': 'notint',
            },
        )
        self.assertFormError(response, 'form', 'capital', _('Enter a whole number.'))

    def test_import_error03(self):
        "Required field without column or default value."
        user = self.login()

        lines = [('Capital',), ('1000',)]  # No 'Name'

        doc = self._build_csv_doc(lines, separator=';')
        url = self._build_import_url(FakeOrganisation)
        response = self.assertPOST200(
            url,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'has_header': True,
                'user': user.id,
                'name_colselect': 0,
                'capital_colselect': 1,
            },
        )
        self.assertFormError(response, 'form', 'name', _('This field is required.'))

    def test_import_error04(self):
        "Required custom-field without column or default value."
        user = self.login()

        create_cf = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeContact),
        )
        cf1 = create_cf(field_type=CustomField.STR, name='Dogtag')
        cf2 = create_cf(field_type=CustomField.INT, name='Eva number', is_required=True)

        lines = [('Ayanami', )]
        doc = self._build_csv_doc(lines, separator=';')
        url = self._build_import_url(FakeContact)
        response = self.assertPOST200(
            url,
            data={
                **self.lv_import_data,
                'document': doc.id,
                'user': user.id,

                f'custom_field-{cf1.id}_colselect': 0,

                f'custom_field-{cf2.id}_colselect': 0,
                # f'custom_field-{cf2.id}_defval': 1,
            },
        )
        self.assertFormError(
            response, 'form', f'custom_field-{cf2.id}',
            _('This field is required.')
        )
        self.assertNotIn(f'custom_field-{cf1.id}', response.context['form'].errors)

    @override_settings(MAX_JOBS_PER_USER=1)
    def test_import_error05(self):
        "Max jobs."
        user = self.login()
        Job.objects.create(
            user=user,
            type_id=mass_import_type.id,
            language='en',
            status=Job.STATUS_WAIT,
        )

        response = self.assertGET200(self._build_import_url(FakeContact), follow=True)
        self.assertRedirects(response, reverse('creme_core__my_jobs'))

    def test_credentials01(self):
        "Creation credentials for imported model."
        user = self.login(
            is_superuser=False, allowed_apps=['creme_core'],
            creatable_models=[FakeOrganisation],  # Not Contact
        )
        self.assertFalse(user.has_perm_to_create(FakeContact))
        self.assertGET403(self._build_import_url(FakeContact))

    def test_credentials02(self):
        "Creation credentials for 'auxiliary' models."
        user = self.login(
            is_superuser=False,
            allowed_apps=['creme_core', 'documents'],
            creatable_models=[FakeContact, FakeOrganisation, Document],
        )

        doc = self._build_csv_doc([('Ayanami', 'Rei', 'Pilot')])
        response = self.assertPOST200(
            self._build_import_url(FakeContact),
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
        self.assertFormError(response, 'form', 'position', 'You can not create instances')

    def test_credentials03(self):
        "Creation credentials for related entities."
        user = self.login(
            is_superuser=False,
            allowed_apps=['creme_core', 'documents'],
            creatable_models=[FakeContact, Document],  # Not Organisation
        )

        employed = RelationType.objects.smart_update_or_create(
            ('test-subject_employed_by', 'is an employee of'),
            ('test-object_employed_by',  'employs'),
        )[0]
        doc = self._build_csv_doc([('Ayanami', 'Rei', 'NERV')])
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
            response, 'form', 'dyn_relations',
            _('You are not allowed to create: %(model)s') % {'model': 'Test Organisation'}
        )

    def test_import_with_update01(self):
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        shinji = create_contact(first_name='Shinji', last_name='Ikari')
        gendo  = create_contact(first_name='Gendo',  last_name='Ikari')

        loves = RelationType.objects.smart_update_or_create(
            ('test-subject_loving', 'is loving'),
            ('test-object_loving',  'is loved by'),
        )[0]

        create_ptype = CremePropertyType.objects.smart_update_or_create
        ptype1 = create_ptype(str_pk='test-prop_cute',   text='Really cute in her suit')
        ptype2 = create_ptype(str_pk='test-blue_haired', text='Has blue hairs')

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
        doc = self._build_csv_doc([
            (d['first_name'], d['last_name'], d['phone'], d['email'])
            for d in (rei_info, asuka_info)
        ])
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
                    (loves.id, shinji),
                    (loves.id, gendo),
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
        self.assertRelationCount(1, rei, loves.id, gendo)
        self.assertRelationCount(1, rei, loves.id, shinji)  # <== not 2 !
        self.get_object_or_fail(CremeProperty, type=ptype2, creme_entity=rei.id)
        self.get_object_or_fail(CremeProperty, type=ptype1, creme_entity=rei.id)  # <= not 2 !

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
        "Several existing entities found"
        user = self.login()

        last_name = 'Ayanami'
        first_name = 'Rei'

        create_contact = partial(
            FakeContact.objects.get_or_create, user=user, last_name=last_name,
        )
        create_contact(first_name='Lei')
        create_contact(first_name='Rey')

        count = FakeContact.objects.count()

        doc = self._build_csv_doc([(last_name, first_name)])
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

        results = self._get_job_results(job)
        self.assertEqual(1, len(results))

        jr_errors = [r for r in results if r.messages]
        self.assertEqual(1, len(jr_errors))

        jr_error = jr_errors[0]
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
        user = self.login()

        last_name = 'Ayanami'
        first_name = 'Rei'

        c = FakeContact.objects.create(user=user, last_name=last_name, first_name='Lei')
        c.trash()

        count = FakeContact.objects.count()

        doc = self._build_csv_doc([(last_name, first_name)])
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
        user = self.login(
            is_superuser=False, allowed_apps=['creme_core', 'documents'],
            creatable_models=[FakeContact, Document],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                # | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
            ctype=FakeContact,
        )

        last_name = 'Ayanami'
        first_name = 'Rei'

        c = FakeContact.objects.create(
            user=self.other_user, last_name=last_name, first_name='Lei',
        )
        self.assertTrue(user.has_perm_to_view(c))
        self.assertFalse(user.has_perm_to_change(c))

        count = FakeContact.objects.count()

        doc = self._build_csv_doc([(last_name, first_name)])
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
        user = self.login()

        civ1, civ2 = FakeCivility.objects.all()[:2]

        last_name = 'Ayanami'
        create_contact = partial(FakeContact.objects.create, user=user, last_name=last_name)
        contact1 = create_contact(civility=civ1)
        contact2 = create_contact(civility=civ2)

        count = FakeContact.objects.count()

        email = 'ayanami@nerv.jp'

        url = self._build_import_url(FakeContact)
        doc = self._build_csv_doc([(last_name, civ2.title, email)])

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
        user = self.login()

        doc = self._build_csv_doc([('Rei', 'Ayanami', 'Pilot')])
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
            response, 'form', 'position',
            _('Select a valid choice. "{value}" is not one of the'
              ' available sub-field.').format(value='invalid')
        )

    def test_fields_config_hidden(self):
        user = self.login()

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
        doc = self._build_csv_doc([
            (
                rei_info['first_name'], rei_info['last_name'],
                rei_info['phone'], rei_info['email'],
            ),
        ])
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
        user = self.login()

        required_fname = 'phone'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[(required_fname, {FieldsConfig.REQUIRED: True})],
        )

        info = [
            {'first_name': 'Rei',   'last_name': 'Ayanami', required_fname: '111111'},
            {'first_name': 'Asuka', 'last_name': 'Langley', required_fname: ''},
        ]
        doc = self._build_csv_doc([
            (c_info['first_name'], c_info['last_name'], c_info[required_fname])
            for c_info in info
        ])

        url = self._build_import_url(FakeContact)
        data = {
            **self.lv_import_data,
            'document': doc.id,
            'user': user.id,
        }
        response1 = self.client.post(url, follow=True, data=data)
        self.assertFormError(
            response1, 'form', required_fname, _('This field is required.'),
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

        jr_errors = [r for r in jresults if r.messages]
        self.assertEqual(1, len(jr_errors))

        jr_error = jr_errors[0]
        self.assertIsNone(jr_error.entity)
        self.assertListEqual(
            [_('The field «{}» has been configured as required.').format(_('Phone number'))],
            jr_error.messages,
        )

    def test_resume(self):
        user = self.login()
        lines = [
            ('Rei',   'Ayanami'),
            ('Asuka', 'Langley'),
        ]

        rei_line = lines[0]
        rei = FakeContact.objects.create(
            user=user, first_name=rei_line[0], last_name=rei_line[1],
        )

        count = FakeContact.objects.count()
        doc = self._build_csv_doc(lines)
        response = self.client.post(
            self._build_import_url(FakeContact), follow=True,
            data={**self.lv_import_data, 'document': doc.id, 'user': user.id},
        )
        self.assertNoFormError(response)

        job = self._get_job(response)
        MassImportJobResult.objects.create(job=job, entity=rei)  # We simulate an interrupted job

        mass_import_type.execute(job)
        self.assertEqual(count + 1, FakeContact.objects.count())

        asuka_line = lines[1]
        self.get_object_or_fail(FakeContact, first_name=asuka_line[0], last_name=asuka_line[1])

    def _aux_test_dl_errors(self, doc_builder, result_builder, ext, header=False):
        "CSV, no header."
        user = self.login()

        first_name = 'Unchô'
        last_name = 'Kan-u'
        birthday = '1995'
        lines = [('First name',   'Last name', 'Birthday')] if header else []
        lines.append((first_name, last_name,   birthday))      # Error
        lines.append(('Asuka',    'Langley',   '01-02-1997'))  # OK

        doc = doc_builder(lines)
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
        user = self.login()
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
        self.login(is_superuser=False)
        job = Job.objects.create(
            user=self.other_user,
            type_id=mass_import_type.id,
            language='en',
            status=Job.STATUS_WAIT,
            # raw_data='',
        )

        self.assertGET403(self._build_dl_errors_url(job))
