# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.utils.encoding import force_unicode
    from django.utils.translation import ugettext as _
    from django.utils.unittest.case import skipIf

    from creme.creme_core.models import RelationType, Relation, CremePropertyType, CremeProperty, HeaderFilter, HeaderFilterItem

    from creme.creme_core.tests.views.base import ViewsTestCase

    from creme.persons.models import Contact, Organisation
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


try:
    from creme.creme_core.utils.xlrd_utils import XlrdReader
    from creme.creme_core.registry import export_backend_registry
    XlsImport = not 'xls' in export_backend_registry.iterkeys()
except Exception as e:
    XlsImport = True

__all__ = ('CSVExportViewsTestCase',)


class CSVExportViewsTestCase(ViewsTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config', 'persons')
        cls.ct = ct = ContentType.objects.get_for_model(Contact)
        HeaderFilter.objects.filter(entity_type=ct).delete()

    def _build_hf_n_contacts(self):
        user = self.user

        create_orga = partial(Organisation.objects.create, user=user)
        bebop     = create_orga(name='Bebop')
        swordfish = create_orga(name='Swordfish')

        rtype_pilots = RelationType.create(('test-subject_pilots', 'pilots'),
                                           ('test-object_pilots',  'is piloted by')
                                          )[0]

        create_ptype = CremePropertyType.create
        ptype_beautiful = create_ptype(str_pk='test-prop_beautiful', text='is beautiful')
        ptype_girl      = create_ptype(str_pk='test-prop_girl',      text='is a girl')

        create_contact = partial(Contact.objects.create, user=user)
        contacts = dict((first_name, create_contact(first_name=first_name, last_name=last_name))
                            for first_name, last_name in [('Spike', 'Spiegel'),
                                                          ('Jet', 'Black'),
                                                          ('Faye', 'Valentine'),
                                                          ('Edward', 'Wong')
                                                         ]
                        )

        create_rel = partial(Relation.objects.create, user=user, type=rtype_pilots)
        create_rel(subject_entity=contacts['Jet'],   object_entity=bebop)
        create_rel(subject_entity=contacts['Spike'], object_entity=bebop)
        create_rel(subject_entity=contacts['Spike'], object_entity=swordfish)

        create_prop = CremeProperty.objects.create
        create_prop(type=ptype_girl,      creme_entity=contacts['Faye'])
        create_prop(type=ptype_girl,      creme_entity=contacts['Edward'])
        create_prop(type=ptype_beautiful, creme_entity=contacts['Faye'])

        hf = HeaderFilter.create(pk='test-hf_contact', name='Contact view', model=Contact)
        hf_items =[HeaderFilterItem.build_4_field(model=Contact, name='civility'),
                   HeaderFilterItem.build_4_field(model=Contact, name='last_name'),
                   HeaderFilterItem.build_4_field(model=Contact, name='first_name'),
                   HeaderFilterItem.build_4_relation(rtype=rtype_pilots),
                   #TODO: build_4_customfield
                   HeaderFilterItem.build_4_functionfield(func_field=Contact.function_fields.get('get_pretty_properties')),
                  ]
        hf.set_items(hf_items)

        return hf_items

    def _build_url(self, ct, method='download', doc_type='csv'):
        return '/creme_core/list_view/%s/%s/%s' % (method, ct.id, doc_type)

    def _set_listview_state(self):
        lv_url = Contact.get_lv_absolute_url()
        self.assertGET200(lv_url) #set the current list view state...

        return lv_url

    def test_export_error01(self): # Assert doc_type in ('xls', 'csv')
        self.login()
        lv_url = self._set_listview_state()

        self.assertGET404(self._build_url(self.ct, doc_type='exe'), data={'list_url': lv_url})

    def test_list_view_export_header(self):
        self.login()
        hf_items = self._build_hf_n_contacts()
        lv_url = self._set_listview_state()
        url = self._build_url(self.ct, method='download_header')
        response = self.assertGET200(url, data={'list_url': lv_url})

        self.assertEqual([u','.join(u'"%s"' % hfi.title for hfi in hf_items)],
                         [force_unicode(line) for line in response.content.splitlines()]
                        )

    @skipIf(XlsImport, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_xls_export_header(self):
        self.login()
        hf_items = self._build_hf_n_contacts()
        lv_url = self._set_listview_state()

        response = self.assertGET200(self._build_url(self.ct, method='download_header', doc_type='xls'),
                                     data={'list_url': lv_url}, follow=True
                                    )

        result = list(XlrdReader(None, file_contents=response.content))
        self.assertEqual(1, len(result))
        self.assertEqual(result[0], [hfi.title for hfi in hf_items])

    def test_list_view_export01(self):
        "csv"
        self.login()
        hf_items = self._build_hf_n_contacts()
        lv_url = self._set_listview_state()

        response = self.assertGET200(self._build_url(self.ct), data={'list_url': lv_url})

        #TODO: sort the relations/properties by they verbose_name ??
        result = [force_unicode(line) for line in response.content.splitlines()]
        self.assertEqual(6, len(result))
        self.assertEqual(result[0], u','.join(u'"%s"' % hfi.title for hfi in hf_items))
        self.assertEqual(result[1], u'"","Black","Jet","Bebop",""')
        self.assertEqual(result[2], u'"%s","Creme","Fulbert","",""' % _(u'Mister'))
        self.assertIn(result[3], (u'"","Spiegel","Spike","Bebop/Swordfish",""',
                                  u'"","Spiegel","Spike","Swordfish/Bebop",""')
                     )
        self.assertIn(result[4], (u'"","Valentine","Faye","","is a girl/is beautiful"',
                                  u'"","Valentine","Faye","","is beautiful/is a girl"')
                     )
        self.assertEqual(result[5], u'"","Wong","Edward","","is a girl"')

    def test_list_view_export02(self):
        "scsv"
        self.login()
        hf_items = self._build_hf_n_contacts()
        lv_url = self._set_listview_state()

        response = self.assertGET200(self._build_url(self.ct, doc_type='scsv'), data={'list_url': lv_url})

        #TODO: sort the relations/properties by they verbose_name ??
        result = map(force_unicode, response.content.splitlines())
        self.assertEqual(6, len(result))
        self.assertEqual(result[0], u';'.join(u'"%s"' % hfi.title for hfi in hf_items))
        self.assertEqual(result[1], u'"";"Black";"Jet";"Bebop";""')
        self.assertEqual(result[2], u'"%s";"Creme";"Fulbert";"";""' % _('Mister'))
        self.assertIn(result[3], (u'"";"Spiegel";"Spike";"Bebop/Swordfish";""',
                                  u'"";"Spiegel";"Spike";"Swordfish/Bebop";""')
                     )
        self.assertIn(result[4], (u'"";"Valentine";"Faye";"";"is a girl/is beautiful"',
                                  u'"";"Valentine";"Faye";"";"is beautiful/is a girl"')
                     )
        self.assertEqual(result[5], u'"";"Wong";"Edward";"";"is a girl"')

    def test_list_view_export03(self):
        "'export' credential"
        self.login(is_superuser=False, allowed_apps=['creme_core', 'persons'])
        self._build_hf_n_contacts()
        url = self._build_url(self.ct)
        data = {'list_url': self._set_listview_state()}
        self.assertGET403(url, data=data)

        self.role.exportable_ctypes = [self.ct] # set the 'export' credentials
        self.assertGET200(url, data=data)

    @skipIf(XlsImport, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_xls_export01(self):
        self.login()
        hf_items = self._build_hf_n_contacts()
        lv_url = self._set_listview_state()

        response = self.assertGET200(self._build_url(self.ct, doc_type='xls'), data={'list_url': lv_url}, follow=True)

        result = list(XlrdReader(None, file_contents=response.content))
        self.assertEqual(6, len(result))
        self.assertEqual(result[0], [hfi.title for hfi in hf_items])
        self.assertEqual(result[1], ["", "Black", "Jet", "Bebop", ""])
        self.assertEqual(result[2], [_('Mister'), "Creme", "Fulbert", "", ""])
        self.assertIn(result[3], (["", "Spiegel", "Spike", "Bebop/Swordfish", ""],
                                  ["", "Spiegel", "Spike", "Swordfish/Bebop", ""]))
        self.assertIn(result[4], (["", "Valentine", "Faye", "", "is a girl/is beautiful"],
                                  ["", "Valentine", "Faye", "", "is beautiful/is a girl"]))
        self.assertEqual(result[5], ["", "Wong", "Edward", "", "is a girl"])
