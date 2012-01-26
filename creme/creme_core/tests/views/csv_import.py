# -*- coding: utf-8 -*-

try:
    from tempfile import NamedTemporaryFile

    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import CremePropertyType, CremeProperty, RelationType, Relation
    from creme_core.tests.views.base import ViewsTestCase

    from persons.models import Contact, Organisation, Position, Sector

    from documents.models import Document, Folder, FolderCategory
except Exception as e:
    print 'Error:', e


__all__ = ('CSVImportViewsTestCase', )


class CSVImportViewsTestCase(ViewsTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')
        self.doc = None

    def tearDown(self):
        if self.doc:
            self.doc.filedata.delete() #clean

    def _build_doc(self, lines, separator=','):
        content = u'\n'.join(separator.join(u'"%s"' % item for item in line) for line in lines)
        content = str(content.encode('utf8'))

        tmpfile = NamedTemporaryFile()
        tmpfile.write(content)
        tmpfile.flush()

        tmpfile.file.seek(0)

        category = FolderCategory.objects.create(id=10, name=u'Test category')
        folder = Folder.objects.create(user=self.user, title=u'Test folder',
                                       parent_folder=None,
                                       category=category,
                                      )

        title = 'Test doc'
        response = self.client.post('/documents/document/add', follow=True,
                                    data={
                                            'user':        self.user.id,
                                            'title':       title,
                                            'description': 'CSV file for contacts',
                                            'filedata':    tmpfile.file,
                                            'folder':      folder.id,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        #try:
        with self.assertNoException():
            self.doc = Document.objects.get(title=title)
        #except Exception as e:
            #self.fail(str(e))

        return self.doc

    def _build_url(self):
        ct = ContentType.objects.get_for_model(Contact)
        return '/creme_core/list_view/import_csv/%s?list_url=%s' % (ct.id, Contact.get_lv_absolute_url())

    def test_import01(self):
        self.login()

        self.assertFalse(Contact.objects.exists())

        lines = [("Ayanami", "Rei"),
                 ("Asuka",   "Langley"),
                ]

        doc = self._build_doc(lines)
        url = self._build_url()
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        #try:
        with self.assertNoException():
            response.context['form']
        #except Exception as e:
            #self.fail(str(e))

        response = self.client.post(url, data={
                                                'csv_step':     0,
                                                'csv_document': doc.id,
                                                #csv_has_header
                                              }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        #try:
        with self.assertNoException():
            form = response.context['form']
        #except Exception as e:
            #self.fail(str(e))

        self.assertIn('value="1"', unicode(form['csv_step']))

        response = self.client.post(url, data={
                                                'csv_step':     1,
                                                'csv_document': doc.id,
                                                #csv_has_header

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

                                                'billing_address_colselect':    0,
                                                'billing_po_box_colselect':     0,
                                                'billing_city_colselect':       0,
                                                'billing_state_colselect':      0,
                                                'billing_zipcode_colselect':    0,
                                                'billing_country_colselect':    0,
                                                'billing_department_colselect': 0,

                                                'shipping_address_colselect':    0,
                                                'shipping_po_box_colselect':     0,
                                                'shipping_city_colselect':       0,
                                                'shipping_state_colselect':      0,
                                                'shipping_zipcode_colselect':    0,
                                                'shipping_country_colselect':    0,
                                                'shipping_department_colselect': 0,
                                              }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        #try:
        with self.assertNoException():
            form = response.context['form']
        #except Exception as e:
            #self.fail(str(e))

        self.assertEqual(0,          len(form.import_errors))
        self.assertEqual(len(lines), form.imported_objects_count)
        self.assertEqual(len(lines), form.lines_count)

        self.assertEqual(len(lines), Contact.objects.count())

        for first_name, last_name in lines:
            #try:
            with self.assertNoException():
                contact = Contact.objects.get(first_name=first_name, last_name=last_name)
            #except Exception as e:
                #self.fail(str(e))

            self.assertEqual(self.user, contact.user)
            #self.assert_(contact.billing_address is None) #TODO: fail ?!

    def test_import02(self): #use header, default value, model search and create, properties, fixed and dynamic relations
        self.login()

        self.assertFalse(Position.objects.exists())
        self.assertFalse(Sector.objects.exists())

        ptype = CremePropertyType.create(str_pk='test-prop_cute', text='Really cure in her suit')

        employed, _srt = RelationType.create(('persons-subject_employed_by', 'is an employee of'),
                                             ('persons-object_employed_by',  'employs')
                                            )
        loves, _srt    = RelationType.create(('test-subject_loving', 'is loving'),
                                             ('test-object_loving',  'is loved by')
                                            )

        nerv = Organisation.objects.create(user=self.user, name='Nerv')
        shinji = Contact.objects.create(user=self.user, first_name='Shinji', last_name='Ikari')

        pos_title = 'Pilot'
        city = 'Tokyo'
        lines = [('First name', 'Last name', 'Position', 'Sector', 'City', 'Organisation'),
                 ('Ayanami',    'Rei',       pos_title,  'Army',   city,   nerv.name),
                 ('Asuka',      'Langley',   pos_title,  'Army',   '',     nerv.name),
                ]

        doc = self._build_doc(lines)
        url = self._build_url()
        response = self.client.post(url, data={
                                                'csv_step':       0,
                                                'csv_document':   doc.id,
                                                'csv_has_header': True,
                                              }
                                   )
        self.assertEqual(200, response.status_code)

        form = response.context['form']
        self.assertIn('value="1"',    unicode(form['csv_step']))
        self.assertIn('value="True"', unicode(form['csv_has_header']))

        default_descr = 'A cute pilot'
        response = self.client.post(url, data={
                                                'csv_step':       1,
                                                'csv_document':   doc.id,
                                                'csv_has_header': True,

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

                                                'billing_address_colselect':    0,
                                                'billing_po_box_colselect':     0,
                                                'billing_city_colselect':       5,
                                                'billing_state_colselect':      0,
                                                'billing_zipcode_colselect':    0,
                                                'billing_country_colselect':    0,
                                                'billing_department_colselect': 0,

                                                'shipping_address_colselect':    0,
                                                'shipping_po_box_colselect':     0,
                                                'shipping_city_colselect':       0,
                                                'shipping_state_colselect':      0,
                                                'shipping_zipcode_colselect':    0,
                                                'shipping_country_colselect':    0,
                                                'shipping_department_colselect': 0,
                                              }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)

        #try:
        with self.assertNoException():
            form = response.context['form']
        #except Exception as e:
            #self.fail(str(e))

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
            #try:
            with self.assertNoException():
                contact = Contact.objects.get(first_name=first_name, last_name=last_name)
            #except Exception as e:
                #self.fail(str(e))

            self.assertEqual(default_descr, contact.description)
            self.assertEqual(position,      contact.position)
            self.assertEqual(1,             CremeProperty.objects.filter(type=ptype, creme_entity=contact.id).count())
            self.assertEqual(1,             Relation.objects.filter(subject_entity=contact, type=loves, object_entity=shinji).count())
            self.assertEqual(1,             Relation.objects.filter(subject_entity=contact, type=employed, object_entity=nerv).count())


        rei = Contact.objects.get(first_name=lines[1][0])
        self.assertEqual(city, rei.billing_address.city)

        doc.filedata.delete() #clean

    def test_import03(self): #create entities to link with them
        self.login()
        self.assertFalse(Organisation.objects.exists())

        employed, _srt = RelationType.create(('persons-subject_employed_by', 'is an employee of'),
                                             ('persons-object_employed_by',  'employs')
                                            )
        orga_name = 'Nerv'
        doc = self._build_doc([('Ayanami', 'Rei', orga_name)])
        response = self.client.post(self._build_url(),
                                    data={
                                            'csv_step':       1,
                                            'csv_document':   doc.id,
                                            #'csv_has_header': True,

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

                                            'billing_address_colselect':    0,
                                            'billing_po_box_colselect':     0,
                                            'billing_city_colselect':       0,
                                            'billing_state_colselect':      0,
                                            'billing_zipcode_colselect':    0,
                                            'billing_country_colselect':    0,
                                            'billing_department_colselect': 0,

                                            'shipping_address_colselect':    0,
                                            'shipping_po_box_colselect':     0,
                                            'shipping_city_colselect':       0,
                                            'shipping_state_colselect':      0,
                                            'shipping_zipcode_colselect':    0,
                                            'shipping_country_colselect':    0,
                                            'shipping_department_colselect': 0,
                                         }
                                   )
        self.assertEqual(200, response.status_code)
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

    def test_import04(self): #other separator
        self.login()

        self.assertFalse(Contact.objects.exists())

        lines = [(u'First name', u'Last name'),
                 (u'Unchô',      u'Kan-u'),
                 (u'Gentoku',    u'Ryûbi'),
                ]

        doc = self._build_doc(lines, separator=';')

        url = self._build_url()

        response = self.client.post(url, data={
                                                'csv_step':     0,
                                                'csv_document': doc.id,
                                              }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertIn('value="1"', unicode(response.context['form']['csv_step']))

        response = self.client.post(url, data={
                                                'csv_step':       1,
                                                'csv_document':   doc.id,
                                                'csv_has_header': True,

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

                                                'billing_address_colselect':    0,
                                                'billing_po_box_colselect':     0,
                                                'billing_city_colselect':       0,
                                                'billing_state_colselect':      0,
                                                'billing_zipcode_colselect':    0,
                                                'billing_country_colselect':    0,
                                                'billing_department_colselect': 0,

                                                'shipping_address_colselect':    0,
                                                'shipping_po_box_colselect':     0,
                                                'shipping_city_colselect':       0,
                                                'shipping_state_colselect':      0,
                                                'shipping_zipcode_colselect':    0,
                                                'shipping_country_colselect':    0,
                                                'shipping_department_colselect': 0,
                                              }
                                   )
        self.assertEqual(200, response.status_code)
        self.assertNoFormError(response)
        self.assertEqual([], list(response.context['form'].import_errors))

        self.assertEqual(len(lines) - 1, Contact.objects.count())

        for first_name, last_name in lines[1:]:
            #try:
            with self.assertNoException():
                contact = Contact.objects.get(first_name=first_name, last_name=last_name)
            #except Exception as e:
                #self.fail(str(e))
