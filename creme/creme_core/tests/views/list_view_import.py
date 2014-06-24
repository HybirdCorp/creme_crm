# -*- coding: utf-8 -*-

try:
    from functools import partial
    from tempfile import NamedTemporaryFile

    from django.utils.translation import ugettext as _
    from django.utils.unittest.case import skipIf
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import CremePropertyType, CremeProperty, RelationType, Relation
    from creme.creme_core.tests.views.base import ViewsTestCase

    from creme.persons.models import Contact, Organisation, Position, Sector

    from creme.documents.models import Document, Folder, FolderCategory
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


try:
    from creme.creme_core.utils.xlwt_utils import XlwtWriter
    from creme.creme_core.registry import import_backend_registry
    XlsImport = not 'xls' in import_backend_registry.iterkeys()
except:
    XlsImport = True

__all__ = ('CSVImportViewsTestCase', )


class CSVImportBaseTestCaseMixin(object):
    clean_files_in_teardown = True #see CremeTestCase

    def _build_file(self, content, extension=None):
        tmpfile = NamedTemporaryFile(suffix=".%s" % extension if extension else '')
        tmpfile.write(content)
        tmpfile.flush()

        return tmpfile

    def _build_doc(self, tmpfile):
        tmpfile.file.seek(0)
        category = FolderCategory.objects.create(id=10, name=u'Test category')
        folder = Folder.objects.create(user=self.user, title=u'Test folder',
                                       parent_folder=None,
                                       category=category,
                                      )

        title = 'Test doc'
        response = self.client.post('/documents/document/add', follow=True,
                                    data={'user':        self.user.id,
                                          'title':       title,
                                          'description': 'CSV file for contacts',
                                          'filedata':    tmpfile,
                                          'folder':      folder.id,
                                         }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            doc = Document.objects.get(title=title)

        return doc

    def _build_csv_doc(self, lines, separator=',', extension='csv'):
        content = u'\n'.join(separator.join(u'"%s"' % item for item in line) for line in lines)
        content = str(content.encode('utf8'))

        tmpfile = self._build_file(content, extension)

        return self._build_doc(tmpfile)

    def _build_xls_doc(self, lines, extension='xls'):
        tmpfile = self._build_file('', extension)
        wb = XlwtWriter()
        for line in lines:
            wb.writerow(line)
        wb.save(tmpfile.name)

        return self._build_doc(tmpfile)

    def _build_import_url(self, model):
        ct = ContentType.objects.get_for_model(model)
        return '/creme_core/list_view/import/%s?list_url=%s' % (ct.id, Contact.get_lv_absolute_url())


class CSVImportViewsTestCase(ViewsTestCase, CSVImportBaseTestCaseMixin):
    @classmethod
    def setUpClass(cls):
        ViewsTestCase.setUpClass()

        cls.populate('creme_core', 'creme_config')

        #Contact.objects.all().delete()
        #Organisation.objects.all().delete()
        #Position.objects.all().delete()
        #Sector.objects.all().delete()

        cls.data = {
            'step': 1,
            #'document':   doc.id,
            #'has_header': True,
            #'user':       self.user.id,

            #'first_name_colselect': 1,
            #'last_name_colselect':  2,

            'civility_colselect':    0,
            'description_colselect': 0,
            'skype_colselect':       0,
            'phone_colselect':       0,
            'mobile_colselect':      0,
            'fax_colselect':         0,
            'position_colselect':    0,
            'sector_colselect':      0,
            'email_colselect':       0,
            'url_site_colselect':    0,
            'birthday_colselect':    0,
            'image_colselect':       0,

            #'property_types',
            #'fixed_relations',
            #'dyn_relations',

            'billaddr_address_colselect':    0,  'shipaddr_address_colselect':    0,
            'billaddr_po_box_colselect':     0,  'shipaddr_po_box_colselect':     0,
            'billaddr_city_colselect':       0,  'shipaddr_city_colselect':       0,
            'billaddr_state_colselect':      0,  'shipaddr_state_colselect':      0,
            'billaddr_zipcode_colselect':    0,  'shipaddr_zipcode_colselect':    0,
            'billaddr_country_colselect':    0,  'shipaddr_country_colselect':    0,
            'billaddr_department_colselect': 0,  'shipaddr_department_colselect': 0,
        }

    def _dyn_relations_value(self, rtype, model, column, subfield):
        return '[{"rtype":"%(rtype)s","ctype":"%(ctype)s",' \
                 '"column":"%(column)s","searchfield":"%(search)s"}]' % {
                        'rtype':  rtype.id,
                        'ctype':  ContentType.objects.get_for_model(model).id,
                        'column': column,
                        'search': subfield,
                    }

    def _test_import01(self, builder):
        self.login()

        count = Contact.objects.count()
        lines = [("Rei",   "Ayanami"),
                 ("Asuka", "Langley"),
                ]

        doc = builder(lines)
        url = self._build_import_url(Contact)
        response = self.assertGET200(url)

        with self.assertNoException():
            response.context['form']

        response = self.client.post(url, data={'step':     0,
                                               'document': doc.id,
                                               #has_header
                                              }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        self.assertIn('value="1"', unicode(form['step']))

        response = self.client.post(url, data=dict(self.data, document=doc.id,
                                                   user=self.user.id,
                                                   first_name_colselect=1,
                                                   last_name_colselect=2,
                                                  ),
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        lines_count = len(lines)
        self.assertFalse(list(form.import_errors))
        self.assertEqual(lines_count, form.imported_objects_count)
        self.assertEqual(lines_count, form.lines_count)

        self.assertEqual(count + lines_count, Contact.objects.count())

        for first_name, last_name in lines:
            contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
            self.assertEqual(self.user, contact.user)
            self.assertIsNone(contact.billing_address)

    def _test_import02(self, builder): #use header, default value, model search and create, properties, fixed and dynamic relations
        self.login()

        pos_title  = 'Pilot'
        sctr_title = 'Army'
        #self.assertFalse(Position.objects.exists())
        self.assertFalse(Position.objects.filter(title=pos_title).exists())
        #self.assertFalse(Sector.objects.exists())
        self.assertFalse(Sector.objects.filter(title=sctr_title).exists())

        position_ids = list(Position.objects.values_list('id', flat=True))
        sector_ids   = list(Sector.objects.values_list('id', flat=True))

        ptype = CremePropertyType.create(str_pk='test-prop_cute', text='Really cure in her suit')

        employed = RelationType.create(('persons-subject_employed_by', 'is an employee of'),
                                       ('persons-object_employed_by',  'employs')
                                      )[0]
        loves = RelationType.create(('test-subject_loving', 'is loving'),
                                    ('test-object_loving',  'is loved by')
                                   )[0]

        nerv = Organisation.objects.create(user=self.user, name='Nerv')
        shinji = Contact.objects.create(user=self.user, first_name='Shinji', last_name='Ikari')
        contact_count = Contact.objects.count()

        city = 'Tokyo'
        lines = [('First name', 'Last name', 'Position', 'Sector', 'City', 'Organisation'),
                 ('Rei',        'Ayanami',   pos_title,  sctr_title,   city,   nerv.name),
                 ('Asuka',      'Langley',   pos_title,  sctr_title,   '',     nerv.name),
                ]

        doc = builder(lines)
        url = self._build_import_url(Contact)
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
                        url,
                        data=dict(self.data, document=doc.id, has_header=True,
                                    user=self.user.id,
                                    first_name_colselect=1,
                                    last_name_colselect=2,

                                    description_colselect=0,
                                    description_defval=default_descr,

                                    position_colselect=3,
                                    position_subfield='title',
                                    position_create=True,

                                    sector_colselect=4,
                                    sector_subfield='title',
                                    #sector_create=False,

                                    property_types=[ptype.id],
                                    fixed_relations='[{"rtype":"%s","ctype":"%s","entity":"%s"}]'  % (
                                                            loves.id, shinji.entity_type_id, shinji.id
                                                        ),
                                    dyn_relations=self._dyn_relations_value(employed, Organisation, 6, 'name'),

                                    billaddr_city_colselect=5,
                                    )
                    )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        lines_count = len(lines) - 1 # '-1' for header
        self.assertEqual(lines_count, len(form.import_errors)) #sector not found
        self.assertEqual(lines_count, form.imported_objects_count)
        self.assertEqual(lines_count, form.lines_count)
        self.assertEqual(contact_count + lines_count, Contact.objects.count())

        #positions = Position.objects.all()
        positions = Position.objects.exclude(id__in=position_ids)
        self.assertEqual(1, len(positions))
        #self.assertEqual(pos_count + 1, len(positions))

        position = positions[0]
        self.assertEqual(pos_title, position.title)

        #self.assertFalse(Sector.objects.exists())
        self.assertFalse(Sector.objects.exclude(id__in=sector_ids).exists())

        for first_name, last_name, pos_title, sector_title, city_name, orga_name in lines[1:]:
            contact = self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)
            self.assertEqual(default_descr, contact.description)
            self.assertEqual(position,      contact.position)
            self.get_object_or_fail(CremeProperty, type=ptype, creme_entity=contact.id)
            self.assertRelationCount(1, contact, loves.id, shinji)
            self.assertRelationCount(1, contact, employed.id, nerv)

        rei = Contact.objects.get(first_name=lines[1][0])
        self.assertEqual(city, rei.billing_address.city)

    def _test_import03(self, builder):
        "Create entities to link with them"
        self.login()
        contact_ids = list(Contact.objects.values_list('id', flat=True))

        orga_name = 'Nerv'
        self.assertFalse(Organisation.objects.filter(name=orga_name))

        employed = RelationType.create(('persons-subject_employed_by', 'is an employee of'),
                                       ('persons-object_employed_by',  'employs')
                                      )[0]
        doc = builder([('Ayanami', 'Rei', orga_name)])
        response = self.client.post(self._build_import_url(Contact),
                                    data=dict(self.data, document=doc.id,
                                              user=self.user.id,
                                              first_name_colselect=1,
                                              last_name_colselect=2,

                                              dyn_relations=self._dyn_relations_value(employed, Organisation, 3, 'name'),
                                              dyn_relations_can_create=True,
                                             ),
                                   )
        self.assertNoFormError(response)

        form = response.context['form']
        self.assertEqual(0, len(form.import_errors)) #sector not found
        self.assertEqual(1, form.imported_objects_count)

        #contacts = Contact.objects.all()
        contacts = Contact.objects.exclude(id__in=contact_ids)
        self.assertEqual(1, len(contacts))

        rei = contacts[0]
        relations = Relation.objects.filter(subject_entity=rei, type=employed)
        self.assertEqual(1, len(relations))

        employer = relations[0].object_entity.get_real_entity()
        self.assertIsInstance(employer, Organisation)
        self.assertEqual(orga_name, employer.name)

    def test_csv_import01(self):
        return self._test_import01(self._build_csv_doc)

    def test_csv_import02(self):
        return self._test_import02(self._build_csv_doc)

    def test_csv_import03(self):
        return self._test_import03(self._build_csv_doc)

    @skipIf(XlsImport, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_xls_import01(self):
        return self._test_import01(self._build_xls_doc)

    @skipIf(XlsImport, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_xls_import02(self):
        return self._test_import02(self._build_xls_doc)

    @skipIf(XlsImport, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_xls_import03(self):
        return self._test_import03(self._build_xls_doc)

    def test_csv_import04(self): 
        "Other separator"
        self.login()
        contact_ids = list(Contact.objects.values_list('id', flat=True))

        #self.assertFalse(Contact.objects.exists())

        lines = [(u'First name', u'Last name'),
                 (u'Unchô',      u'Kan-u'),
                 (u'Gentoku',    u'Ryûbi'),
                ]

        doc = self._build_csv_doc(lines, separator=';')
        url = self._build_import_url(Contact)
        response = self.client.post(url, data={'step':     0,
                                               'document': doc.id,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertIn('value="1"', unicode(response.context['form']['step']))

        response = self.client.post(url, data=dict(self.data, document=doc.id,
                                                   has_header=True,
                                                   user=self.user.id,
                                                   first_name_colselect=1,
                                                   last_name_colselect=2,
                                                  ),
                                   )
        self.assertNoFormError(response)
        self.assertEqual([], list(response.context['form'].import_errors))

        #self.assertEqual(len(lines) - 1, Contact.objects.count())
        self.assertEqual(len(lines) - 1, Contact.objects.exclude(id__in=contact_ids).count())

        for first_name, last_name in lines[1:]:
            self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)

    def test_import_error01(self):
        "Form error: unknown extension"
        self.login()

        doc = self._build_doc(self._build_file('Non Empty File...', 'doc'))
        response = self.assertPOST200(self._build_import_url(Contact),
                                      data={'step': 0, 'document': doc.id}
                                     )
        self.assertFormError(response, 'form', None,
                             [_(u"Error reading document, unsupported file type: %s.") %
                                    doc.filedata.name
                             ]
                            )

    def test_import_error02(self):
        "Validate default value"
        self.login()

        lines = [('Name', 'Capital'),
                 ('Nerv', '1000'),
                ]

        doc = self._build_csv_doc(lines, separator=';')
        url = self._build_import_url(Organisation)
        response = self.client.post(url, data=dict(self.data, document=doc.id,
                                                   has_header=True,
                                                   user=self.user.id,
                                                   name_colselect=1,

                                                   capital_colselect=2,
                                                   capital_defval='notint',
                                                  ),
                                   )
        self.assertFormError(response, 'form', 'capital', _('Enter a whole number.'))

    def test_import_error03(self):
        "Required field witout column or default value"
        self.login()

        lines = [('Capital',), ('1000',)] #No 'Name'

        doc = self._build_csv_doc(lines, separator=';')
        url = self._build_import_url(Organisation)
        response = self.client.post(url, data=dict(self.data, document=doc.id,
                                                   has_header=True,
                                                   user=self.user.id,
                                                   name_colselect=0,
                                                   capital_colselect=1,
                                                  ),
                                   )
        self.assertFormError(response, 'form', 'name', _('This field is required.'))

    def test_credentials01(self):
        "Creation credentials for imported model"
        self.login(is_superuser=False, allowed_apps=['persons'],
                   creatable_models=[Organisation], #not Contact
                  )
        self.assertGET403(self._build_import_url(Contact))

    def test_credentials02(self):
        "Creation credentials for 'auxiliary' models"
        self.login(is_superuser=False, allowed_apps=['persons', 'documents'],
                   creatable_models=[Contact, Organisation, Document],
                  )

        doc = self._build_csv_doc([('Ayanami', 'Rei', 'Pilot')])
        response = self.assertPOST200(self._build_import_url(Contact),
                                      data=dict(self.data, document=doc.id,
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
        self.login(is_superuser=False, allowed_apps=['persons', 'documents'],
                   creatable_models=[Contact, Document], #not Organisation
                  )

        employed = RelationType.create(('persons-subject_employed_by', 'is an employee of'),
                                       ('persons-object_employed_by',  'employs')
                                      )[0]
        doc = self._build_csv_doc([('Ayanami', 'Rei', 'NERV')])
        response = self.assertPOST200(self._build_import_url(Contact),
                                      data=dict(self.data, document=doc.id,
                                                user=self.user.id,
                                                first_name_colselect=2,
                                                last_name_colselect=1,

                                                dyn_relations=self._dyn_relations_value(employed, Organisation, 3, 'name'),
                                                dyn_relations_can_create=True,
                                               ),
                                     )
        self.assertFormError(response, 'form', 'dyn_relations', 
                             _(u'You are not allowed to create: %s') % _(u'Organisation')
                            )

    def test_import_with_update01(self):
        self.login()
        user = self.user

        rei_info   = {'first_name': 'Rei',   'last_name': 'Ayanami', 'phone': '111111'}
        asuka_info = {'first_name': 'Asuka', 'last_name': 'Langley', 'phone': '222222'}

        rei = Contact.objects.get_or_create(first_name=rei_info['first_name'],
                                            last_name=rei_info['last_name'],
                                            defaults={'user': user},
                                           )[0]
        self.assertNotEqual(rei_info['phone'], rei.phone)

        #Should not be modified, even is 'first_name' is searched
        rei2 = Contact.objects.get_or_create(first_name=rei_info['first_name'],
                                            last_name='Iyanima',
                                            defaults={'user': user},
                                           )[0]

        self.assertFalse(Contact.objects.filter(last_name=asuka_info['last_name'])
                                        .exists()
                        )

        count = Contact.objects.count()
        doc = self._build_csv_doc([(d['first_name'], d['last_name'], d['phone'])
                                    for d in (rei_info, asuka_info)
                                  ]
                                 )
        response = self.client.post(self._build_import_url(Contact),
                                    data=dict(self.data, document=doc.id,
                                              user=user.id,
                                              key_fields=['first_name', 'last_name'],
                                              first_name_colselect=1,
                                              last_name_colselect=2,
                                              phone_colselect=3,
                                             ),
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(0, len(form.import_errors))
        self.assertEqual(2, form.lines_count)
        self.assertEqual(1, form.imported_objects_count)
        self.assertEqual(1, form.updated_objects_count)

        self.assertEqual(count + 1, Contact.objects.count())
        self.assertEqual(rei_info['phone'], self.refresh(rei).phone)
        self.assertIsNone(self.refresh(rei2).phone)
        self.get_object_or_fail(Contact, **asuka_info)

    def test_import_with_update02(self):
        "Several existing entities found"
        self.login()
        user = self.user

        last_name = 'Ayanami'
        first_name = 'Rei'

        create_contact = partial(Contact.objects.get_or_create, user=user,
                                 last_name=last_name,
                                )
        create_contact(first_name='Lei')
        create_contact(first_name='Rey')

        count = Contact.objects.count()

        doc = self._build_csv_doc([(last_name, first_name)])
        response = self.client.post(self._build_import_url(Contact),
                                    data=dict(self.data, document=doc.id,
                                              user=user.id,
                                              key_fields=['last_name'],
                                              last_name_colselect=1,
                                              first_name_colselect=2,
                                             ),
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(1, form.lines_count)
        self.assertEqual(1, form.imported_objects_count)
        self.assertEqual(0, form.updated_objects_count)

        self.assertEqual(count + 1, Contact.objects.count())
        rei = self.get_object_or_fail(Contact, last_name=last_name, first_name=first_name)

        errors = form.import_errors
        self.assertEqual(1, len(errors))

        error = iter(errors).next()
        self.assertEqual([last_name, first_name], error.line)
        self.assertEqual(_('Several entities corresponding to the research have been found. '
                           'So a new entity have been created to avoid errors.'
                          ),
                         unicode(error.message)
                        )
        self.assertEqual(rei, error.instance)


    #def test_import_with_updateXX(self): TODO: test search on FK ? exclude them ??
