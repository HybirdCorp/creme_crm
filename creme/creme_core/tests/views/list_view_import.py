# -*- coding: utf-8 -*-

try:
    from tempfile import NamedTemporaryFile

    from django.utils.translation import ugettext as _
    from django.utils.unittest.case import skipIf
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import CremePropertyType, CremeProperty, RelationType, Relation
    from creme.creme_core.tests.views.base import ViewsTestCase


    from creme.persons.models import Contact, Organisation, Position, Sector

    from creme.documents.models import Document, Folder, FolderCategory
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


try:
    from creme.creme_core.utils.xlwt_utils import XlwtWriter
    from creme.creme_core.registry import import_backend_registry
    XlsImport = not 'xls' in import_backend_registry.iterkeys()
except:
    XlsImport = True

__all__ = ('CSVImportViewsTestCase', )


class CSVImportBaseTestCaseMixin(object):
    doc = None

    def tearDown(self):
        if self.doc:
            self.doc.filedata.delete() #clean

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
            self.doc = Document.objects.get(title=title)

        return self.doc

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
        cls.populate('creme_core', 'creme_config')

        Contact.objects.all().delete()
        Organisation.objects.all().delete()
        Position.objects.all().delete()
        Sector.objects.all().delete()

    def _test_import01(self, builder):
        self.login()

        self.assertFalse(Contact.objects.exists())

        lines = [("Ayanami", "Rei"),
                 ("Asuka",   "Langley"),
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

        response = self.client.post(url, data={
                                                'step':     1,
                                                'document': doc.id,
                                                #has_header

                                                'user': self.user.id,

                                                'civility_colselect':  0,

                                                'first_name_colselect': 1,
                                                'last_name_colselect':  2,

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

                                                'billaddr_address_colselect':    0,
                                                'billaddr_po_box_colselect':     0,
                                                'billaddr_city_colselect':       0,
                                                'billaddr_state_colselect':      0,
                                                'billaddr_zipcode_colselect':    0,
                                                'billaddr_country_colselect':    0,
                                                'billaddr_department_colselect': 0,

                                                'shipaddr_address_colselect':    0,
                                                'shipaddr_po_box_colselect':     0,
                                                'shipaddr_city_colselect':       0,
                                                'shipaddr_state_colselect':      0,
                                                'shipaddr_zipcode_colselect':    0,
                                                'shipaddr_country_colselect':    0,
                                                'shipaddr_department_colselect': 0,
                                              }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        self.assertEqual(0,          len(form.import_errors))
        self.assertEqual(len(lines), form.imported_objects_count)
        self.assertEqual(len(lines), form.lines_count)

        self.assertEqual(len(lines), Contact.objects.count())

        for first_name, last_name in lines:
            with self.assertNoException():
                contact = Contact.objects.get(first_name=first_name, last_name=last_name)

            self.assertEqual(self.user, contact.user)
            #self.assert_(contact.billing_address is None) #TODO: fail ?!

    def _test_import02(self, builder): #use header, default value, model search and create, properties, fixed and dynamic relations
        self.login()

        self.assertFalse(Position.objects.exists())
        self.assertFalse(Sector.objects.exists())

        ptype = CremePropertyType.create(str_pk='test-prop_cute', text='Really cure in her suit')

        employed = RelationType.create(('persons-subject_employed_by', 'is an employee of'),
                                       ('persons-object_employed_by',  'employs')
                                      )[0]
        loves = RelationType.create(('test-subject_loving', 'is loving'),
                                    ('test-object_loving',  'is loved by')
                                   )[0]

        nerv = Organisation.objects.create(user=self.user, name='Nerv')
        shinji = Contact.objects.create(user=self.user, first_name='Shinji', last_name='Ikari')

        pos_title = 'Pilot'
        city = 'Tokyo'
        lines = [('First name', 'Last name', 'Position', 'Sector', 'City', 'Organisation'),
                 ('Ayanami',    'Rei',       pos_title,  'Army',   city,   nerv.name),
                 ('Asuka',      'Langley',   pos_title,  'Army',   '',     nerv.name),
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
        response = self.client.post(url, data={
                                                'step':       1,
                                                'document':   doc.id,
                                                'has_header': True,

                                                'user': self.user.id,

                                                'civility_colselect': 0,

                                                'first_name_colselect': 1,
                                                'last_name_colselect':  2,

                                                'description_colselect': 0,
                                                'description_defval':    default_descr,

                                                'skype_colselect':       0,
                                                'phone_colselect':       0,
                                                'mobile_colselect':      0,
                                                'fax_colselect':         0,

                                                'position_colselect': 3,
                                                'position_subfield':  'title',
                                                'position_create':    True,

                                                'sector_colselect': 4,
                                                'sector_subfield':  'title',
                                                #'sector_create':    False,

                                                'email_colselect':       0,
                                                'url_site_colselect':    0,
                                                'birthday_colselect':    0,
                                                'image_colselect':       0,

                                                'property_types':  [ptype.id],
                                                'fixed_relations': '[{"rtype":"%s","ctype":"%s","entity":"%s"}]'  % (
                                                                            loves.id, shinji.entity_type_id, shinji.id
                                                                        ),
                                                'dyn_relations':    '[{"rtype":"%(rtype)s","ctype":"%(ctype)s","column":"%(column)s","searchfield":"%(search)s"}]'  % {
                                                                            'rtype': employed.id,
                                                                            'ctype': ContentType.objects.get_for_model(Organisation).id,
                                                                            'column': 6,
                                                                            'search': 'name',
                                                                        },

                                                'billaddr_address_colselect':    0,
                                                'billaddr_po_box_colselect':     0,
                                                'billaddr_city_colselect':       5,
                                                'billaddr_state_colselect':      0,
                                                'billaddr_zipcode_colselect':    0,
                                                'billaddr_country_colselect':    0,
                                                'billaddr_department_colselect': 0,

                                                'shipaddr_address_colselect':    0,
                                                'shipaddr_po_box_colselect':     0,
                                                'shipaddr_city_colselect':       0,
                                                'shipaddr_state_colselect':      0,
                                                'shipaddr_zipcode_colselect':    0,
                                                'shipaddr_country_colselect':    0,
                                                'shipaddr_department_colselect': 0,
                                              }
                                   )
        self.assertNoFormError(response)

        with self.assertNoException():
            form = response.context['form']

        count = len(lines) - 1 # '-1' for header
        self.assertEqual(count,     len(form.import_errors)) #sector not found
        self.assertEqual(count,     form.imported_objects_count)
        self.assertEqual(count,     form.lines_count)
        self.assertEqual(count + 1, Contact.objects.count()) #+ 1 : because of shinji

        positions = Position.objects.all()
        self.assertEqual(1, len(positions))

        position = positions[0]
        self.assertEqual(pos_title, position.title)

        self.assertFalse(Sector.objects.exists())

        for first_name, last_name, pos_title, sector_title, city_name, orga_name in lines[1:]:
            with self.assertNoException():
                contact = Contact.objects.get(first_name=first_name, last_name=last_name)

            self.assertEqual(default_descr, contact.description)
            self.assertEqual(position,      contact.position)
            self.assertEqual(1,             CremeProperty.objects.filter(type=ptype, creme_entity=contact.id).count())
            self.assertRelationCount(1, contact, loves.id, shinji)
            self.assertRelationCount(1, contact, employed.id, nerv)

        rei = Contact.objects.get(first_name=lines[1][0])
        self.assertEqual(city, rei.billing_address.city)

        doc.filedata.delete() #clean TODO: improve (not cleaned if there is a failure...)

    def _test_import03(self, builder):
        "Create entities to link with them"
        self.login()
        self.assertFalse(Organisation.objects.exists())

        employed = RelationType.create(('persons-subject_employed_by', 'is an employee of'),
                                       ('persons-object_employed_by',  'employs')
                                      )[0]
        orga_name = 'Nerv'
        doc = builder([('Ayanami', 'Rei', orga_name)])
        response = self.client.post(self._build_import_url(Contact),
                                    data={
                                            'step':       1,
                                            'document':   doc.id,
                                            #'has_header': True,

                                            'user': self.user.id,

                                            'civility_colselect': 0,

                                            'first_name_colselect': 1,
                                            'last_name_colselect':  2,

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

                                            #'property_types':,
                                            #'fixed_relations':,
                                            'dyn_relations':    '[{"rtype":"%(rtype)s","ctype":"%(ctype)s","column":"%(column)s","searchfield":"%(search)s"}]'  % {
                                                                        'rtype':  employed.id,
                                                                        'ctype':  ContentType.objects.get_for_model(Organisation).id,
                                                                        'column': 3,
                                                                        'search': 'name',
                                                                    },
                                            'dyn_relations_can_create': True,

                                            'billaddr_address_colselect':    0,
                                            'billaddr_po_box_colselect':     0,
                                            'billaddr_city_colselect':       0,
                                            'billaddr_state_colselect':      0,
                                            'billaddr_zipcode_colselect':    0,
                                            'billaddr_country_colselect':    0,
                                            'billaddr_department_colselect': 0,

                                            'shipaddr_address_colselect':    0,
                                            'shipaddr_po_box_colselect':     0,
                                            'shipaddr_city_colselect':       0,
                                            'shipaddr_state_colselect':      0,
                                            'shipaddr_zipcode_colselect':    0,
                                            'shipaddr_country_colselect':    0,
                                            'shipaddr_department_colselect': 0,
                                         }
                                   )
        self.assertNoFormError(response)

        form = response.context['form']
        self.assertEqual(0, len(form.import_errors)) #sector not found
        self.assertEqual(1, form.imported_objects_count)

        contacts = Contact.objects.all()
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

    def test_csv_import04(self): #other separator
        self.login()

        self.assertFalse(Contact.objects.exists())

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

        response = self.client.post(url, data={
                                                'step':       1,
                                                'document':   doc.id,
                                                'has_header': True,

                                                'user': self.user.id,

                                                'civility_colselect':  0,

                                                'first_name_colselect': 1,
                                                'last_name_colselect':  2,

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

                                                'billaddr_address_colselect':    0,
                                                'billaddr_po_box_colselect':     0,
                                                'billaddr_city_colselect':       0,
                                                'billaddr_state_colselect':      0,
                                                'billaddr_zipcode_colselect':    0,
                                                'billaddr_country_colselect':    0,
                                                'billaddr_department_colselect': 0,

                                                'shipaddr_address_colselect':    0,
                                                'shipaddr_po_box_colselect':     0,
                                                'shipaddr_city_colselect':       0,
                                                'shipaddr_state_colselect':      0,
                                                'shipaddr_zipcode_colselect':    0,
                                                'shipaddr_country_colselect':    0,
                                                'shipaddr_department_colselect': 0,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual([], list(response.context['form'].import_errors))

        self.assertEqual(len(lines) - 1, Contact.objects.count())

        for first_name, last_name in lines[1:]:
            self.get_object_or_fail(Contact, first_name=first_name, last_name=last_name)

    def test_import_error01(self): #Form error: unknown extension
        self.login()

        self.assertFalse(Contact.objects.exists())

        lines = [(u'First name', u'Last name'),
                 (u'Unchô',      u'Kan-u'),
                 (u'Gentoku',    u'Ryûbi'),
                ]
        extension = 'doc'
        doc = self._build_doc(self._build_file('Non Empty File...', extension))
        url = self._build_import_url(Contact)
        response = self.assertPOST200(url, data={'step':     0,
                                               'document': doc.id,
                                                }
                                     )
        self.assertFormError(response, 'form', None,
                             [_(u"Error reading document, unsupported file type: %s.") % doc.filedata.name])
