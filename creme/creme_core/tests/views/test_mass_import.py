# -*- coding: utf-8 -*-

try:
    from decimal import Decimal
    from functools import partial
    import json
    from unittest import skipIf

    from django.contrib.contenttypes.models import ContentType
    from django.core.urlresolvers import reverse
    from django.template.defaultfilters import slugify
    from django.test.utils import override_settings
    from django.utils.encoding import smart_unicode
    from django.utils.timezone import now
    from django.utils.translation import ugettext as _, ungettext

    from .base import ViewsTestCase, CSVImportBaseTestCaseMixin, BrickTestCaseMixin, skipIfNoXLSLib

    from creme.creme_core.bricks import MassImportJobErrorsBrick, JobErrorsBrick
    from creme.creme_core.creme_jobs import mass_import_type, batch_process_type
    from creme.creme_core.models import (CremePropertyType, CremeProperty,
            RelationType, Relation, FieldsConfig, CustomField, CustomFieldEnumValue,
            Job, MassImportJobResult,
            FakeContact, FakeOrganisation, FakeAddress, FakePosition, FakeSector, FakeEmailCampaign)
    from creme.creme_core.utils import update_model_instance

    from creme.documents.models import Document
    from creme.documents.tests.base import skipIfCustomDocument, skipIfCustomFolder
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))

try:
    from creme.creme_core.utils.xlrd_utils import XlrdReader
    from creme.creme_core.backends import export_backend_registry

    XlsMissing = 'xls' not in export_backend_registry.iterkeys()
except Exception:
    XlsMissing = True


@skipIfCustomDocument
@skipIfCustomFolder
class MassImportViewsTestCase(ViewsTestCase, CSVImportBaseTestCaseMixin, BrickTestCaseMixin):
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
        # ViewsTestCase.setUpClass()
        super(MassImportViewsTestCase, cls).setUpClass()
        # cls.populate('creme_core')
        Job.objects.all().delete()

        cls.ct = ContentType.objects.get_for_model(FakeContact)

    def _build_dl_errors_url(self, job):
        return reverse('creme_core__dl_mass_import_errors', args=(job.id,))

    def _dyn_relations_value(self, rtype, model, column, subfield):
        return '[{"rtype":"%(rtype)s","ctype":"%(ctype)s",' \
                 '"column":"%(column)s","searchfield":"%(search)s"}]' % {
                        'rtype':  rtype.id,
                        'ctype':  ContentType.objects.get_for_model(model).id,
                        'column': column,
                        'search': subfield,
                    }

    def _test_import01(self, builder):
        user = self.login()

        count = FakeContact.objects.count()
        lines = [('Rei',   'Ayanami'),
                 ('Asuka', 'Langley'),
                ]

        doc = builder(lines)
        url = self._build_import_url(FakeContact)
        response = self.assertGET200(url)

        with self.assertNoException():
            response.context['form']

        response = self.client.post(url, data={'step':     0,
                                               'document': doc.id,
                                               # has_header
                                              }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        self.assertIn('value="1"', unicode(form['step']))

        response = self.client.post(url, follow=True,
                                    data=dict(self.lv_import_data,
                                              document=doc.id,
                                              user=user.id,
                                             ),
                                   )
        self.assertNoFormError(response)

        # with self.assertNoException():
        #     form = response.context['form']
        jobs = Job.objects.all()
        self.assertEqual(1, len(jobs))

        job = jobs[0]
        self.assertEqual(self.user, job.user)
        # self.assertLess((now() - job.created).seconds, 1)
        self.assertIsNone(job.last_run)
        self.assertIsInstance(job.data, dict)
        self.assertEqual(Job.STATUS_WAIT, job.status)
        self.assertIsNone(job.error)
        self.assertFalse(self._get_job_results(job))

        # Properties
        self.assertIs(mass_import_type, job.type)
        self.assertEqual([_(u'Import «{type}» from {doc}').format(
                                type='Test Contact',
                                doc=doc,
                            )
                         ],
                         job.description
                        )  # TODO: description of columns ????

        self.assertRedirects(response, job.get_absolute_url())
        # self.assertContains(response, ' id="%s"' % MassImportJobErrorsBlock.id_)
        tree = self.get_html_tree(response.content)
        self.get_brick_node(tree, MassImportJobErrorsBrick.id_)

        mass_import_type.execute(job)

        lines_count = len(lines)
        # self.assertFalse(list(form.import_errors))
        # self.assertEqual(lines_count, form.imported_objects_count)
        # self.assertEqual(lines_count, form.lines_count)
        self.assertEqual(count + lines_count, FakeContact.objects.count())
        self.assertDatetimesAlmostEqual(now(), job.last_run)

        # self.assertEqual(count + lines_count, Contact.objects.count())

        contacts = []
        for first_name, last_name in lines:
            contact = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
            self.assertEqual(user, contact.user)
            self.assertIsNone(contact.address)

            contacts.append(contact)

        job = self.refresh(job)
        self.assertEqual(Job.STATUS_OK, job.status)
        self.assertIsNone(job.error)
        results = self._get_job_results(job)
        self.assertEqual(2, len(results))
        self.assertEqual(set(contacts), {r.entity.get_real_entity() for r in results})
        self._assertNoResultError(results)
        self.assertIs(results[0].updated, False)

        self.assertEqual([ungettext(u'{counter} «{type}» has been created.',
                                    u'{counter} «{type}» have been created.',
                                    lines_count
                                   ).format(counter=lines_count,
                                            type='Test Contacts',
                                           ),
                          ungettext(u'{count} line in the file.',
                                    u'{count} lines in the file.',
                                    lines_count,
                                   ).format(count=lines_count),
                         ],
                         job.stats
                        )

        progress = job.progress
        self.assertIsNone(progress.percentage)
        self.assertEqual(ungettext(u'{count} line has been processed.',
                                   u'{count} lines have been processed.',
                                   lines_count
                                  ).format(count=lines_count),
                         progress.label
                        )

        # Reload brick -----------
        brick_id = MassImportJobErrorsBrick.id_
        response = self.assertGET200(reverse('creme_core__reload_job_bricks', args=(job.id,)),
                                     data={'brick_id': brick_id},
                                    )
        with self.assertNoException():
            result = json.loads(response.content)

        self.assertIsInstance(result, list)
        self.assertEqual(1, len(result))

        result = result[0]
        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))
        self.assertEqual(brick_id, result[0])
        # self.assertIn(' id="%s"' % brick_id, result[1])
        tree = self.get_html_tree(result[1])
        self.get_brick_node(tree, brick_id)

        self.assertGET404(reverse('creme_core__reload_job_bricks', args=(job.id,)),
                          data={'brick_id': JobErrorsBrick.id_},
                         )

    def _test_import02(self, builder):
        "Use header, default value, model search and create, properties, fixed and dynamic relations"
        self.login()

        pos_title  = 'Pilot'
        sctr_title = 'Army'
        self.assertFalse(FakePosition.objects.filter(title=pos_title).exists())
        self.assertFalse(FakeSector.objects.filter(title=sctr_title).exists())

        position_ids = list(FakePosition.objects.values_list('id', flat=True))
        sector_ids   = list(FakeSector.objects.values_list('id', flat=True))

        ptype = CremePropertyType.create(str_pk='test-prop_cute', text='Really cute in her suit')

        employed = RelationType.create(('persons-subject_employed_by', 'is an employee of'),
                                       ('persons-object_employed_by',  'employs')
                                      )[0]
        loves = RelationType.create(('test-subject_loving', 'is loving'),
                                    ('test-object_loving',  'is loved by')
                                   )[0]

        nerv = FakeOrganisation.objects.create(user=self.user, name='Nerv')
        shinji = FakeContact.objects.create(user=self.user, first_name='Shinji', last_name='Ikari')
        contact_count = FakeContact.objects.count()

        city = 'Tokyo'
        lines = [('First name', 'Last name', 'Position', 'Sector',   'City', 'Organisation'),
                 ('Rei',        'Ayanami',   pos_title,  sctr_title, city,   nerv.name),
                 ('Asuka',      'Langley',   pos_title,  sctr_title, '',     nerv.name),
                ]

        doc = builder(lines)
        url = self._build_import_url(FakeContact)
        response = self.assertPOST200(url, data={'step':       0,
                                                 'document':   doc.id,
                                                 'has_header': True,
                                                }
                                     )

        form = response.context['form']
        self.assertIn('value="1"',    unicode(form['step']))
        self.assertIn('value="True"', unicode(form['has_header']))

        default_descr = 'A cute pilot'
        response = self.client.post(
                          url, follow=True,
                          data=dict(self.lv_import_data,
                                    document=doc.id, has_header=True,
                                    user=self.user.id,

                                    description_colselect=0,
                                    description_defval=default_descr,

                                    position_colselect=3,
                                    position_subfield='title',
                                    position_defval='',  # The browser POST an empty string
                                    position_create=True,

                                    sector_colselect=4,
                                    sector_subfield='title',
                                    sector_defval='',  # The browser POST an empty string
                                    # sector_create=False,

                                    property_types=[ptype.id],
                                    fixed_relations='[{"rtype":"%s","ctype":"%s","entity":"%s"}]'  % (
                                                            loves.id, shinji.entity_type_id, shinji.id
                                                        ),
                                    dyn_relations=self._dyn_relations_value(employed, FakeOrganisation, 6, 'name'),

                                    address_city_colselect=5,
                                   )
                    )
        self.assertNoFormError(response)

        # with self.assertNoException():
        #     form = response.context['form']
        job = self._execute_job(response)

        lines_count = len(lines) - 1  # '-1' for header
        # self.assertEqual(lines_count, len(form.import_errors))  # Sector not found
        # self.assertEqual(lines_count, form.imported_objects_count)
        # self.assertEqual(lines_count, form.lines_count)
        self.assertEqual(contact_count + lines_count, FakeContact.objects.count())

        positions = FakePosition.objects.exclude(id__in=position_ids)
        self.assertEqual(1, len(positions))

        position = positions[0]
        self.assertEqual(pos_title, position.title)

        self.assertFalse(FakeSector.objects.exclude(id__in=sector_ids).exists())

        for first_name, last_name, pos_title, sector_title, city_name, orga_name in lines[1:]:
            contact = self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)
            self.assertEqual(default_descr, contact.description)
            self.assertEqual(position,      contact.position)
            self.get_object_or_fail(CremeProperty, type=ptype, creme_entity=contact.id)
            self.assertRelationCount(1, contact, loves.id, shinji)
            self.assertRelationCount(1, contact, employed.id, nerv)

        self.assertFalse(FakeContact.objects.filter(last_name=lines[0][1]))  # Header must not be used

        rei = FakeContact.objects.get(first_name=lines[1][0])
        address = rei.address
        self.assertIsInstance(address, FakeAddress)
        self.assertEqual(city, address.city)

        results = self._get_job_results(job)
        self.assertEqual(lines_count, len(results))
        self.assertEqual([ungettext(u'{counter} «{type}» has been created.',
                                    u'{counter} «{type}» have been created.',
                                    lines_count
                                  ).format(counter=lines_count, type='Test Contacts'),
                          ungettext(u'{count} line in the file.',
                                    u'{count} lines in the file.',
                                    lines_count,
                                   ).format(count=lines_count),
                         ],
                         job.stats
                        )
        self.assertTrue(all(r.messages for r in results))  # Sector not found

    def _test_import03(self, builder):
        "Create entities to link with them"
        self.login()
        contact_ids = list(FakeContact.objects.values_list('id', flat=True))

        orga_name = 'Nerv'
        self.assertFalse(FakeOrganisation.objects.filter(name=orga_name))

        employed = RelationType.create(('persons-subject_employed_by', 'is an employee of'),
                                       ('persons-object_employed_by',  'employs')
                                      )[0]
        doc = builder([('Ayanami', 'Rei', orga_name)])
        response = self.client.post(self._build_import_url(FakeContact), follow=True,
                                    data=dict(self.lv_import_data, document=doc.id,
                                              user=self.user.id,

                                              dyn_relations=self._dyn_relations_value(employed, FakeOrganisation, 3, 'name'),
                                              dyn_relations_can_create=True,
                                             ),
                                   )
        self.assertNoFormError(response)

        # form = response.context['form']
        # self.assertEqual(0, len(form.import_errors))  # Sector not found
        # self.assertEqual(1, form.imported_objects_count)
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

    def test_csv_import01(self):
        return self._test_import01(self._build_csv_doc)

    def test_csv_import02(self):
        return self._test_import02(self._build_csv_doc)

    def test_csv_import03(self):
        return self._test_import03(self._build_csv_doc)

    @skipIfNoXLSLib
    def test_xls_import01(self):
        return self._test_import01(self._build_xls_doc)

    @skipIfNoXLSLib
    def test_xls_import02(self):
        return self._test_import02(self._build_xls_doc)

    @skipIfNoXLSLib
    def test_xls_import03(self):
        return self._test_import03(self._build_xls_doc)

    def test_csv_import04(self): 
        "Other separator"
        user = self.login()
        contact_ids = list(FakeContact.objects.values_list('id', flat=True))

        lines = [(u'First name', u'Last name'),
                 (u'Unchô',      u'Kan-u'),
                 (u'Gentoku',    u'Ryûbi'),
                ]

        doc = self._build_csv_doc(lines, separator=';')
        url = self._build_import_url(FakeContact)
        response = self.client.post(url, data={'step':     0,
                                               'document': doc.id,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertIn('value="1"', unicode(response.context['form']['step']))

        response = self.client.post(url, follow=True,
                                    data=dict(self.lv_import_data, document=doc.id,
                                              has_header=True,
                                              user=user.id,
                                             ),
                                   )
        self.assertNoFormError(response)
        # self.assertEqual([], list(response.context['form'].import_errors))

        job = self._execute_job(response)
        self.assertEqual(len(lines) - 1, FakeContact.objects.exclude(id__in=contact_ids).count())

        for first_name, last_name in lines[1:]:
            self.get_object_or_fail(FakeContact, first_name=first_name, last_name=last_name)

        results = self._get_job_results(job)
        self.assertEqual(2, len(results))
        self._assertNoResultError(results)

    def _get_cf_values(self, cf, entity):
        return self.get_object_or_fail(cf.get_value_class(), custom_field=cf, entity=entity)

    def test_csv_import_customfields01(self): 
        "CustomField.INT, STR & FLOAT, update, cast error"
        user = self.login()

        create_cf = partial(CustomField.objects.create, content_type=self.ct)
        cf_int = create_cf(name='Size (cm)',   field_type=CustomField.INT)
        cf_dec = create_cf(name='Weight (kg)', field_type=CustomField.FLOAT)
        cf_str = create_cf(name='Nickname',    field_type=CustomField.STR)

        lines = [('First name', 'Last name', 'Size', 'Weight'),
                 (u'Unchô',      u'Kan-u',   '180',    '55'),
                 (u'Gentoku',    u'Ryûbi',   '155',    ''),
                 (u'Hakufu',     u'Sonsaku', '',       '50.2'),
                 (u'Shimei',     u'Ryomou',  'notint', '48'),
                ]

        kanu = FakeContact.objects.create(user=user, first_name=lines[1][0],
                                          last_name=lines[1][1],
                                         )
        cf_int.get_value_class()(custom_field=cf_dec, entity=kanu).set_value_n_save(Decimal('56'))
        cf_str.get_value_class()(custom_field=cf_str, entity=kanu).set_value_n_save(u"Kan")

        contact_ids = list(FakeContact.objects.values_list('id', flat=True))

        doc = self._build_csv_doc(lines)
        response = self.client.post(self._build_import_url(FakeContact),
                                    follow=True,
                                    data=dict(self.lv_import_data, document=doc.id,
                                              has_header=True,
                                              user=user.id,
                                              key_fields=['first_name', 'last_name'],
                                              **{'custom_field_%s_colselect' % cf_int.id: 3,
                                                 'custom_field_%s_colselect' % cf_str.id: 0,
                                                 'custom_field_%s_colselect' % cf_dec.id: 4,
                                                }
                                             ),
                                   )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(len(lines) - 2,  # 2 = 1 header + 1 update
                         FakeContact.objects.exclude(id__in=contact_ids).count()
                        )

        def get_contact(line_index):
            line = lines[line_index]
            return self.get_object_or_fail(FakeContact, first_name=line[0], last_name=line[1])

        get_cf_values = self._get_cf_values
        self.assertEqual(180, get_cf_values(cf_int, kanu).value)
        self.assertEqual(Decimal('55'), get_cf_values(cf_dec, kanu).value)
        self.assertEqual(u'Kan', get_cf_values(cf_str, kanu).value)

        ryubi = get_contact(2)
        self.assertEqual(155, get_cf_values(cf_int, ryubi).value)
        self.assertFalse(cf_dec.get_value_class().objects.filter(entity=ryubi))

        sonsaku = get_contact(3)
        self.assertFalse(cf_int.get_value_class().objects.filter(entity=sonsaku))
        self.assertEqual(Decimal('50.2'), get_cf_values(cf_dec, sonsaku).value)

        ryomou = get_contact(4)
        self.assertFalse(cf_int.get_value_class().objects.filter(entity=ryomou))
        self.assertEqual(Decimal('48'), get_cf_values(cf_dec, ryomou).value)

        # errors = list(response.context['form'].import_errors)
        # self.assertEqual(1, len(errors))
        #
        # error = errors[0]
        # self.assertEqual(list(lines[4]), error.line)
        # self.assertEqual(_('Enter a whole number.'), unicode(error.message))
        # self.assertEqual(ryomou, error.instance)
        results = self._get_job_results(job)
        self.assertEqual(4, len(results))

        jr_errors = [r for r in results if r.messages]
        self.assertEqual(1, len(jr_errors))

        jr_error = jr_errors[0]
        self.assertEqual(list(lines[4]), jr_error.line)
        self.assertEqual([_(u'Enter a whole number.')],  # TODO: add the field verbose name !!
                         jr_error.messages
                        )
        self.assertEqual(ryomou, jr_error.entity.get_real_entity())

    def test_csv_import_customfields02(self): 
        "CustomField.ENUM/MULTI_ENUM (no creation of choice)"
        user = self.login()
        contact_ids = list(FakeContact.objects.values_list('id', flat=True))

        create_cf = partial(CustomField.objects.create, content_type=self.ct)
        cf_enum  = create_cf(name='Attack',  field_type=CustomField.ENUM)
        cf_enum2 = create_cf(name='Drink',   field_type=CustomField.ENUM)
        cf_menum = create_cf(name='Weapons', field_type=CustomField.MULTI_ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        punch = create_evalue(custom_field=cf_enum, value='Punch')
        create_evalue(custom_field=cf_enum, value='Kick')
        create_evalue(custom_field=cf_enum, value='Hold')

        create_evalue(custom_field=cf_enum2, value='Punch')  # Try to annoy the search on 'punch'

        create_evalue(custom_field=cf_menum, value='Sword')
        spear = create_evalue(custom_field=cf_menum, value='Spear')

        lines = [('First name', 'Last name', 'Attack',        'Weapons'),
                 (u'Hakufu',     u'Sonsaku', 'punch',         ''),
                 (u'Unchô',      u'Kan-u',   'strangulation', 'Spear'),
                ]

        doc = self._build_csv_doc(lines)
        response = self.client.post(self._build_import_url(FakeContact),
                                    follow=True,
                                    data=dict(self.lv_import_data, document=doc.id,
                                              has_header=True,
                                              user=user.id,
                                              **{'custom_field_%s_colselect' % cf_enum.id:  3,
                                                 'custom_field_%s_colselect' % cf_enum2.id: 0,
                                                 'custom_field_%s_colselect' % cf_menum.id: 4,
                                                }
                                             ),
                                    )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(len(lines) - 1,  # 1 header
                         FakeContact.objects.exclude(id__in=contact_ids).count()
                        )

        def get_contact(line_index):
            line = lines[line_index]
            return self.get_object_or_fail(FakeContact, first_name=line[0], last_name=line[1])

        get_cf_values = self._get_cf_values
        sonsaku = get_contact(1)
        self.assertEqual(punch, get_cf_values(cf_enum, sonsaku).value)

        kanu = get_contact(2)
        self.assertFalse(cf_enum.get_value_class().objects.filter(entity=kanu))
        self.assertEqual([spear], list(get_cf_values(cf_menum, kanu).value.all()))

        # errors = list(response.context['form'].import_errors)
        # self.assertEqual(1, len(errors))
        #
        # error = errors[0]
        # self.assertEqual(list(lines[2]), error.line)
        # self.assertEqual(_(u'Error while extracting value: tried to retrieve '
        #                    u'the choice "%(value)s" (column %(column)s). '
        #                    u'Raw error: [%(raw_error)s]') % {
        #                         'raw_error': 'CustomFieldEnumValue matching query does not exist.',
        #                         'column':    3,
        #                         'value':     'strangulation',
        #                     },
        #                  unicode(error.message)
        #                 )
        # self.assertEqual(kanu, error.instance)
        results = self._get_job_results(job)
        self.assertEqual(2, len(results))

        jr_errors = [r for r in results if r.messages]
        self.assertEqual(1, len(jr_errors))

        jr_error = jr_errors[0]
        self.assertEqual(list(lines[2]), jr_error.line)
        self.assertEqual([_(u'Error while extracting value: tried to retrieve '
                            u'the choice "%(value)s" (column %(column)s). '
                            u'Raw error: [%(raw_error)s]') % {
                                'raw_error': 'CustomFieldEnumValue matching query does not exist.',
                                'column':    3,
                                'value':     'strangulation',
                            }
                         ],
                         jr_error.messages
                        )
        self.assertEqual(kanu, jr_error.entity.get_real_entity())

    def test_csv_import_customfields03(self): 
        "CustomField.ENUM (creation of choice if not found)"
        user = self.login()
        contact_ids = list(FakeContact.objects.values_list('id', flat=True))

        create_cf = partial(CustomField.objects.create, content_type=self.ct)
        cf_enum  = create_cf(name='Attack',  field_type=CustomField.ENUM)
        cf_menum = create_cf(name='Weapons', field_type=CustomField.MULTI_ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        punch = create_evalue(custom_field=cf_enum,  value='Punch')
        sword = create_evalue(custom_field=cf_menum, value='Sword')

        lines = [('First name', 'Last name', 'Attack',        'Weapons'),
                 (u'Hakufu',     u'Sonsaku', 'punch',         'sword'),
                 (u'Unchô',      u'Kan-u',   'strangulation', 'spear'),
                 (u'Gentoku',    u'Ryûbi',   '',              ''),
                ]

        doc = self._build_csv_doc(lines)
        response = self.client.post(self._build_import_url(FakeContact),
                                    follow=True,
                                    data=dict(self.lv_import_data, document=doc.id,
                                              has_header=True,
                                              user=user.id,
                                              **{'custom_field_%s_colselect' % cf_enum.id: 3,
                                                 'custom_field_%s_create' % cf_enum.id:    True,

                                                 'custom_field_%s_colselect' % cf_menum.id: 4,
                                                 'custom_field_%s_create' % cf_menum.id:    True,
                                                }
                                             ),
                                   )
        self.assertNoFormError(response)

        job = self._execute_job(response)
        self.assertEqual(len(lines) - 1,  # 1 header
                         FakeContact.objects.exclude(id__in=contact_ids).count()
                        )

        def get_contact(line_index):
            line = lines[line_index]
            return self.get_object_or_fail(FakeContact, first_name=line[0], last_name=line[1])

        get_cf_values = self._get_cf_values
        sonsaku = get_contact(1)
        self.assertEqual(punch,   get_cf_values(cf_enum, sonsaku).value)
        self.assertEqual([sword], list(get_cf_values(cf_menum, sonsaku).value.all()))

        kanu = get_contact(2)
        strang = self.get_object_or_fail(CustomFieldEnumValue, custom_field=cf_enum,
                                         value='strangulation',
                                        )
        self.assertEqual(strang, get_cf_values(cf_enum, kanu).value)
        spear = self.get_object_or_fail(CustomFieldEnumValue, custom_field=cf_menum,
                                        value='spear',
                                       )
        self.assertEqual([spear], list(get_cf_values(cf_menum, kanu).value.all()))

        self.assertEqual(2, CustomFieldEnumValue.objects.filter(custom_field=cf_enum).count())  # Not '' choice

        # self.assertEqual(0, len(response.context['form'].import_errors))
        self._assertNoResultError(self._get_job_results(job))

    def test_csv_import_customfields04(self):
        "CustomField.ENUM/MULTI_ENUM: creation credentials"
        self.login(is_superuser=False, allowed_apps=['creme_core', 'documents'],
                   creatable_models=[FakeContact, Document],
                  )

        create_cf = partial(CustomField.objects.create, content_type=self.ct)
        cf_enum  = create_cf(name='Attack',  field_type=CustomField.ENUM)
        cf_menum = create_cf(name='Weapons', field_type=CustomField.MULTI_ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        create_evalue(custom_field=cf_enum,  value='Punch')
        create_evalue(custom_field=cf_menum, value='Sword')

        lines = [('First name', 'Last name', 'Attack',        'Weapons'),
                 (u'Unchô',      u'Kan-u',   'strangulation', 'spear'),
                ]

        doc = self._build_csv_doc(lines)

        def post():
            return self.client.post(self._build_import_url(FakeContact),
                                    follow=True,
                                    data=dict(self.lv_import_data, document=doc.id,
                                              has_header=True,
                                              user=self.user.id,
                                              **{'custom_field_%s_colselect' % cf_enum.id: 3,
                                                 'custom_field_%s_create' % cf_enum.id: True,

                                                 'custom_field_%s_colselect' % cf_menum.id: 4,
                                                 'custom_field_%s_create' % cf_menum.id:    True,
                                                }
                                             ),
                                   )

        response = post()
        self.assertFormError(response, 'form', 'custom_field_%s' % cf_enum.id,
                             'You can not create choices',
                            )
        self.assertFormError(response, 'form', 'custom_field_%s' % cf_menum.id,
                             'You can not create choices',
                            )

        role = self.role 
        role.admin_4_apps = ['creme_config']
        role.save()

        response = post()
        self.assertNoFormError(response)

        self._execute_job(response)
        self.get_object_or_fail(CustomFieldEnumValue, custom_field=cf_enum,
                                value='strangulation',
                               )
        self.get_object_or_fail(CustomFieldEnumValue, custom_field=cf_menum,
                                value='spear',
                               )

    def test_csv_import_customfields05(self): 
        "Default value"
        user = self.login()
        contact_ids = list(FakeContact.objects.values_list('id', flat=True))

        create_cf = partial(CustomField.objects.create, content_type=self.ct)
        cf_int  = create_cf(name='Size (cm)', field_type=CustomField.INT)
        cf_enum = create_cf(name='Attack',    field_type=CustomField.ENUM)
        cf_menum = create_cf(name='Weapons',  field_type=CustomField.MULTI_ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        punch = create_evalue(custom_field=cf_enum,  value='Punch')
        sword = create_evalue(custom_field=cf_menum, value='Sword')

        lines = [('First name', 'Last name', 'Size', 'Attack', 'Weapons'),
                 (u'Unchô',      u'Kan-u',   '',     '',       ''),
                ]

        doc = self._build_csv_doc(lines)

        def post(defint):
            return self.client.post(self._build_import_url(FakeContact),
                                    follow=True,
                                    data=dict(self.lv_import_data, document=doc.id,
                                              has_header=True,
                                              user=user.id,
                                              key_fields=['first_name', 'last_name'],
                                              **{'custom_field_%s_colselect' % cf_int.id: 3,
                                                 'custom_field_%s_defval'    % cf_int.id: defint,

                                                 'custom_field_%s_colselect' % cf_enum.id: 4,
                                                 'custom_field_%s_defval'    % cf_enum.id: str(punch.id),

                                                 'custom_field_%s_colselect' % cf_menum.id: 5,
                                                 'custom_field_%s_defval'    % cf_menum.id: str(sword.id),
                                                }
                                             ),
                                   )

        response = post('notint')
        self.assertFormError(response, 'form', 'custom_field_%s' % cf_int.id, 
                             _(u'Enter a whole number.')
                            )

        response = post('180')
        self.assertNoFormError(response)

        self._execute_job(response)
        self.assertEqual(len(lines) - 1,
                         FakeContact.objects.exclude(id__in=contact_ids).count()
                        )

        line = lines[1]
        kanu = self.get_object_or_fail(FakeContact, first_name=line[0], last_name=line[1])

        get_cf_values = self._get_cf_values
        self.assertEqual(180,   get_cf_values(cf_int,  kanu).value)
        self.assertEqual(punch, get_cf_values(cf_enum, kanu).value)
        self.assertEqual([sword], list(get_cf_values(cf_menum, kanu).value.all()))

    def test_import_error01(self):
        "Form error: unknown extension"
        self.login()

        doc = self._build_doc(self._build_file('Non Empty File...', 'doc'))
        response = self.assertPOST200(self._build_import_url(FakeContact),
                                      data={'step': 0, 'document': doc.id}
                                     )
        self.assertFormError(response, 'form', None,
                             _(u'Error reading document, unsupported file type: %(file)s.') % {
                                    'file': doc.filedata.name,
                                }
                            )

    def test_import_error02(self):
        "Validate default value"
        self.login()

        lines = [('Name', 'Capital'),
                 ('Nerv', '1000'),
                ]

        doc = self._build_csv_doc(lines, separator=';')
        url = self._build_import_url(FakeOrganisation)
        response = self.client.post(url, data=dict(self.lv_import_data, document=doc.id,
                                                   has_header=True,
                                                   user=self.user.id,
                                                   name_colselect=1,

                                                   capital_colselect=2,
                                                   capital_defval='notint',
                                                  ),
                                   )
        self.assertFormError(response, 'form', 'capital', _(u'Enter a whole number.'))

    def test_import_error03(self):
        "Required field without column or default value"
        self.login()

        lines = [('Capital',), ('1000',)]  # No 'Name'

        doc = self._build_csv_doc(lines, separator=';')
        url = self._build_import_url(FakeOrganisation)
        response = self.client.post(url, data=dict(self.lv_import_data, document=doc.id,
                                                   has_header=True,
                                                   user=self.user.id,
                                                   name_colselect=0,
                                                   capital_colselect=1,
                                                  ),
                                   )
        self.assertFormError(response, 'form', 'name', _(u'This field is required.'))

    @override_settings(MAX_JOBS_PER_USER=1)
    def test_import_error04(self):
        "Max jobs"
        user = self.login()
        Job.objects.create(user=user,
                           type_id=mass_import_type.id,
                           language='en',
                          )

        response = self.assertGET200(self._build_import_url(FakeContact), follow=True)
        # self.assertRedirects(response, '/creme_core/job/all')
        self.assertRedirects(response, reverse('creme_core__jobs'))

    def test_credentials01(self):
        "Creation credentials for imported model"
        user = self.login(is_superuser=False, allowed_apps=['creme_core'],
                          creatable_models=[FakeOrganisation],  # Not Contact
                         )
        self.assertFalse(user.has_perm_to_create(FakeContact))
        self.assertGET403(self._build_import_url(FakeContact))

    def test_credentials02(self):
        "Creation credentials for 'auxiliary' models"
        self.login(is_superuser=False, allowed_apps=['creme_core', 'documents'],
                   creatable_models=[FakeContact, FakeOrganisation, Document],
                  )

        doc = self._build_csv_doc([('Ayanami', 'Rei', 'Pilot')])
        response = self.assertPOST200(self._build_import_url(FakeContact),
                                      data=dict(self.lv_import_data, document=doc.id,
                                                user=self.user.id,
                                                first_name_colselect=2,
                                                last_name_colselect=1,

                                                position_colselect=3,
                                                position_subfield='title',
                                                position_create=True,
                                               ),
                                     )
        self.assertFormError(response, 'form', 'position', 'You can not create instances')

    def test_credentials03(self):
        "Creation credentials for related entities"
        self.login(is_superuser=False, allowed_apps=['creme_core', 'documents'],
                   creatable_models=[FakeContact, Document],  # Not Organisation
                  )

        employed = RelationType.create(('persons-subject_employed_by', 'is an employee of'),
                                       ('persons-object_employed_by',  'employs')
                                      )[0]
        doc = self._build_csv_doc([('Ayanami', 'Rei', 'NERV')])
        response = self.assertPOST200(self._build_import_url(FakeContact),
                                      data=dict(self.lv_import_data, document=doc.id,
                                                user=self.user.id,
                                                first_name_colselect=2,
                                                last_name_colselect=1,

                                                dyn_relations=self._dyn_relations_value(employed, FakeOrganisation, 3, 'name'),
                                                dyn_relations_can_create=True,
                                               ),
                                     )
        self.assertFormError(response, 'form', 'dyn_relations', 
                             _(u'You are not allowed to create: %(model)s') % {
                                    'model': u'Test Organisation',
                                }
                            )

    def test_import_with_update01(self):
        user = self.login()

        create_contact = partial(FakeContact.objects.create, user=user)
        shinji = create_contact(first_name='Shinji', last_name='Ikari')
        gendo  = create_contact(first_name='Gendo',  last_name='Ikari')

        loves = RelationType.create(('test-subject_loving', 'is loving'),
                                    ('test-object_loving',  'is loved by')
                                   )[0]

        create_ptype = CremePropertyType.create
        ptype1 = create_ptype(str_pk='test-prop_cute',   text='Really cute in her suit')
        ptype2 = create_ptype(str_pk='test-blue_haired', text='Has blue hairs')

        rei_info   = {'first_name': 'Rei',   'last_name': 'Ayanami', 'phone': '111111', 'email': '\t '}
        asuka_info = {'first_name': 'Asuka', 'last_name': 'Langley', 'phone': '222222', 'email': ''}

        rei_mobile = '54554'
        rei_email  = 'rei.ayanami@nerv.jp'
        rei = FakeContact.objects.get_or_create(first_name=rei_info['first_name'],
                                                last_name=rei_info['last_name'],
                                                defaults={'user': user},
                                               )[0]
        self.assertNotEqual(rei_info['phone'], rei.phone)

        update_model_instance(rei, mobile=rei_mobile, email=rei_email)

        # This relation & this property should not be duplicated
        Relation.objects.create(subject_entity=rei, type=loves, object_entity=shinji, user=user)
        CremeProperty.objects.create(type=ptype1, creme_entity=rei)

        # Should not be modified, even is 'first_name' is searched
        rei2 = FakeContact.objects.get_or_create(first_name=rei_info['first_name'],
                                                 last_name='Iyanima',
                                                 defaults={'user': user},
                                                )[0]

        self.assertFalse(FakeContact.objects.filter(last_name=asuka_info['last_name'])
                                            .exists()
                        )

        count = FakeContact.objects.count()
        doc = self._build_csv_doc([(d['first_name'], d['last_name'], d['phone'], d['email'])
                                        for d in (rei_info, asuka_info)
                                  ]
                                 )
        response = self.client.post(self._build_import_url(FakeContact),
                                    follow=True,
                                    data=dict(self.lv_import_data, document=doc.id,
                                              user=user.id,
                                              key_fields=['first_name', 'last_name'],
                                              phone_colselect=3,
                                              email_colselect=4,
                                              property_types=[ptype1.id, ptype2.id],
                                              fixed_relations='[{"rtype":"%s","ctype":"%s","entity":"%s"},'
                                                              ' {"rtype":"%s","ctype":"%s","entity":"%s"}]'% (
                                                            loves.id, shinji.entity_type_id, shinji.id,
                                                            loves.id, gendo.entity_type_id,  gendo.id,
                                                        ),
                                             ),
                                   )
        self.assertNoFormError(response)
        job = self._execute_job(response)

        # with self.assertNoException():
        #     form = response.context['form']
        #
        # self.assertEqual(0, len(form.import_errors))
        # self.assertEqual(2, form.lines_count)
        # self.assertEqual(1, form.imported_objects_count)
        # self.assertEqual(1, form.updated_objects_count)

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
        self.get_object_or_fail(FakeContact, **asuka_info)

        asuka = self.get_object_or_fail(FakeContact, **asuka_info)
        jresult = self.get_object_or_fail(MassImportJobResult, job=job, entity=asuka)
        self.assertFalse(jresult.updated)

        jresult = self.get_object_or_fail(MassImportJobResult, job=job, entity=rei)
        self.assertTrue(jresult.updated)

        self.assertEqual([ungettext(u'{counter} «{type}» has been created.',
                                    u'{counter} «{type}» have been created.',
                                    1
                                   ).format(counter=1, type='Test Contact'),
                          ungettext(u'{counter} «{type}» has been updated.',
                                    u'{counter} «{type}» have been updated.',
                                    1
                                   ).format(counter=1, type='Test Contact'),
                          ungettext(u'{count} line in the file.',
                                    u'{count} lines in the file.',
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

        create_contact = partial(FakeContact.objects.get_or_create, user=user,
                                 last_name=last_name,
                                 )
        create_contact(first_name='Lei')
        create_contact(first_name='Rey')

        count = FakeContact.objects.count()

        doc = self._build_csv_doc([(last_name, first_name)])
        response = self.client.post(self._build_import_url(FakeContact),
                                    follow=True,
                                    data=dict(self.lv_import_data, document=doc.id,
                                              user=user.id,
                                              key_fields=['last_name'],
                                              last_name_colselect=1,
                                              first_name_colselect=2,
                                             ),
                                   )
        self.assertNoFormError(response)

        # with self.assertNoException():
        #     form = response.context['form']
        #
        # self.assertEqual(1, form.lines_count)
        # self.assertEqual(1, form.imported_objects_count)
        # self.assertEqual(0, form.updated_objects_count)
        job = self._execute_job(response)

        self.assertEqual(count + 1, FakeContact.objects.count())
        rei = self.get_object_or_fail(FakeContact, last_name=last_name, first_name=first_name)

        # errors = form.import_errors
        # self.assertEqual(1, len(errors))
        results = self._get_job_results(job)
        self.assertEqual(1, len(results))

        # error = iter(errors).next()
        # self.assertEqual([last_name, first_name], error.line)
        # self.assertEqual(_('Several entities corresponding to the search have been found. '
        #                    'So a new entity have been created to avoid errors.'
        #                   ),
        #                  unicode(error.message)
        #                 )
        # self.assertEqual(rei, error.instance)
        jr_errors = [r for r in results if r.messages]
        self.assertEqual(1, len(jr_errors))

        jr_error = jr_errors[0]
        self.assertEqual([last_name, first_name], jr_error.line)
        self.assertEqual([_(u'Several entities corresponding to the search have been found. '
                            u'So a new entity have been created to avoid errors.'
                           )
                         ],
                         jr_error.messages
                        )

        self.assertEqual(rei, jr_error.entity.get_real_entity())

    def test_import_with_update03(self):
        "Ignore trashed entities"
        user = self.login()

        last_name = 'Ayanami'
        first_name = 'Rei'

        c = FakeContact.objects.create(user=user, last_name=last_name, first_name='Lei')
        c.trash()

        count = FakeContact.objects.count()

        doc = self._build_csv_doc([(last_name, first_name)])
        response = self.client.post(self._build_import_url(FakeContact), follow=True,
                                    data=dict(self.lv_import_data, document=doc.id,
                                              user=user.id,
                                              key_fields=['last_name'],
                                              last_name_colselect=1,
                                              first_name_colselect=2,
                                             ),
                                   )
        self.assertNoFormError(response)

        # with self.assertNoException():
        #     form = response.context['form']
        #
        # self.assertEqual(1, form.lines_count)
        # self.assertEqual(1, form.imported_objects_count)
        # self.assertEqual(0, form.updated_objects_count)
        job = self._execute_job(response)

        self.assertEqual(count + 1, FakeContact.objects.count())
        self.get_object_or_fail(FakeContact, last_name=last_name, first_name=first_name)

        results = self._get_job_results(job)
        self.assertEqual(1, len(results))

    # def test_import_with_updateXX(self): TODO: test search on FK ? exclude them ??

    def test_fields_config(self):
        user = self.login()

        hidden_fname = 'phone'
        FieldsConfig.create(FakeContact, descriptions=[(hidden_fname, {FieldsConfig.HIDDEN: True})])

        rei_info = {'first_name': 'Rei', 'last_name': 'Ayanami',
                    hidden_fname: '111111', 'email': 'rei.ayanami@nerv.jp',
                   }
        doc = self._build_csv_doc([(rei_info['first_name'], rei_info['last_name'],
                                    rei_info['phone'], rei_info['email'],
                                   )
                                  ]
                                 )
        url = self._build_import_url(FakeContact)
        response = self.client.post(url, data={'step': 0, 'document': doc.id})
        self.assertNoFormError(response)

        with self.assertNoException():
            fields = response.context['form'].fields
            key_choices = {c[0] for c in fields['key_fields'].choices}

        self.assertIn('last_name', key_choices)
        self.assertNotIn(hidden_fname, key_choices)

        self.assertIn('last_name', fields)
        self.assertNotIn(hidden_fname, fields)

        response = self.client.post(url, follow=True,
                                    data=dict(self.lv_import_data, document=doc.id,
                                              user=user.id,
                                              key_fields=['first_name', 'last_name'],
                                              phone_colselect=3,  # Should be ignored
                                              email_colselect=4,
                                             ),
                                   )
        self.assertNoFormError(response)

        self._execute_job(response)
        rei = self.get_object_or_fail(FakeContact, last_name=rei_info['last_name'],
                                      first_name=rei_info['first_name'],
                                      )
        self.assertEqual(rei_info['email'], rei.email)
        self.assertIsNone(getattr(rei, hidden_fname))

    def test_resume(self):
        user = self.login()
        lines = [('Rei',   'Ayanami'),
                 ('Asuka', 'Langley'),
                ]

        rei_line = lines[0]
        rei = FakeContact.objects.create(user=user, first_name=rei_line[0], last_name=rei_line[1])

        count = FakeContact.objects.count()
        doc = self._build_csv_doc(lines)
        response = self.client.post(self._build_import_url(FakeContact), follow=True,
                                    data=dict(self.lv_import_data, document=doc.id, user=user.id),
                                    )
        self.assertNoFormError(response)

        job = self._get_job(response)
        MassImportJobResult.objects.create(job=job, entity=rei)  # We simulate an interrupted job

        mass_import_type.execute(job)
        self.assertEqual(count + 1, FakeContact.objects.count())

        asuka_line = lines[1]
        self.get_object_or_fail(FakeContact, first_name=asuka_line[0], last_name=asuka_line[1])

    def _aux_test_dl_errors(self, doc_builder, result_builder, ext, header=False, follow=False):
        "CSV, no header"
        user = self.login()

        first_name = u'Unchô'
        # first_name = u'Uncho'
        last_name = 'Kan-u'
        birthday = '1995'
        lines = [('First name',   'Last name', 'Birthday')] if header else []
        lines.append((first_name, last_name,   birthday))      # Error
        lines.append(('Asuka',    'Langley',   '01-02-1997'))  # OK

        doc = doc_builder(lines)
        data = dict(self.lv_import_data,
                    document=doc.id,
                    user=user.id,
                    birthday_colselect=3,
                   )

        if header:
           data['has_header'] = 'on'

        response = self.client.post(self._build_import_url(FakeContact),
                                    follow=True, data=data,
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
        self.assertEqual([_(u'Enter a valid date.')], j_error.messages)

        # response = self.assertGET200('/creme_core/mass_import/dl_errors/%s' % job.id, follow=True)
        response = self.assertGET200(self._build_dl_errors_url(job), follow=True)

        # self.assertEqual('attachment; filename=%s-errors.%s' % (slugify(doc.title), ext),
        #                  response['Content-Disposition']
        #                 )
        cdisp = response['Content-Disposition']
        self.assertTrue(cdisp.startswith('attachment; filename=%s-errors' % slugify(doc.title)),
                        'Content-Disposition: not expected: %s' % cdisp
                       )
        self.assertTrue(cdisp.endswith('.%s' % ext))

        result_lines = [['First name',   'Last name', 'Birthday', _(u'Errors')]] if header else []
        result_lines.append([first_name, last_name,   birthday,   _(u'Enter a valid date.')])

        self.assertEqual(result_lines,
                         result_builder(response),
                        )

    def _csv_to_list(self, response):
        separator = u','

        return [[i[1:-1] for i in line.split(separator)]
                    # for line in response.content.splitlines()
                    for line in smart_unicode(response.content).splitlines()
               ]

    def test_dl_errors01(self):
        "CSV, no header"
        self._aux_test_dl_errors(self._build_csv_doc,
                                 result_builder=self._csv_to_list,
                                 ext='csv',
                                 header=False,
                                )

    def test_dl_errors02(self):
        "CSV, header"  # TODO: other separator
        self._aux_test_dl_errors(self._build_csv_doc,
                                 result_builder=self._csv_to_list,
                                 ext='csv',
                                 header=True,
                                )

    @skipIf(XlsMissing, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_dl_errors03(self):
        "XLS"
        def result_builder(response):
            return list(XlrdReader(None, file_contents=response.content))

        self._aux_test_dl_errors(self._build_xls_doc,
                                 result_builder=result_builder,
                                 ext='xls',
                                 header=True,
                                 follow=True,
                                )

    def test_dl_errors04(self):
        "Bad Job type"
        user = self.login()
        job = Job.objects.create(user=user,
                                 type_id=batch_process_type.id,
                                 language='en',
                                 status=Job.STATUS_WAIT,
                                 # raw_data='',
                                )

        self.assertGET404(self._build_dl_errors_url(job))

    def test_dl_errors05(self):
        "Bad user"
        self.login(is_superuser=False)
        job = Job.objects.create(user=self.other_user,
                                 type_id=mass_import_type.id,
                                 language='en',
                                 status=Job.STATUS_WAIT,
                                 # raw_data='',
                                )

        self.assertGET403(self._build_dl_errors_url(job))
