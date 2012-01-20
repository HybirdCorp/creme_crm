# -*- coding: utf-8 -*-

try:
    from django.utils.translation import ugettext as _
    from django.utils.encoding import smart_str, force_unicode
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models import RelationType, Relation, CremePropertyType, CremeProperty, HeaderFilter, HeaderFilterItem
    from creme_core.tests.views.base import ViewsTestCase

    from persons.models import Contact, Organisation
except Exception as e:
    print 'Error:', e


__all__ = ('CSVExportViewsTestCase',)


class CSVExportViewsTestCase(ViewsTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config', 'persons')
        self.ct = ContentType.objects.get_for_model(Contact)

    def _build_hf_n_contacts(self):
        bebop     = Organisation.objects.create(user=self.user, name='Bebop')
        swordfish = Organisation.objects.create(user=self.user, name='Swordfish')

        rtype_pilots, __ = RelationType.create(('test-subject_pilots', 'pilots'),
                                               ('test-object_pilots',  'is piloted by')
                                              )

        ptype_beautiful = CremePropertyType.create(str_pk='test-prop_beautiful', text='is beautiful')
        ptype_girl      = CremePropertyType.create(str_pk='test-prop_girl',      text='is a girl')

        create_contact = Contact.objects.create
        contacts = dict((first_name, create_contact(user=self.user, first_name=first_name, last_name=last_name))
                            for first_name, last_name in [('Spike', 'Spiegel'), ('Jet', 'Black'), ('Faye', 'Valentine'), ('Edward', 'Wong')]
                        )

        Relation.objects.create(user=self.user, subject_entity=contacts['Jet'],   type=rtype_pilots, object_entity=bebop)
        Relation.objects.create(user=self.user, subject_entity=contacts['Spike'], type=rtype_pilots, object_entity=bebop)
        Relation.objects.create(user=self.user, subject_entity=contacts['Spike'], type=rtype_pilots, object_entity=swordfish)

        CremeProperty.objects.create(type=ptype_girl,      creme_entity=contacts['Edward'])
        CremeProperty.objects.create(type=ptype_girl,      creme_entity=contacts['Faye'])
        CremeProperty.objects.create(type=ptype_beautiful, creme_entity=contacts['Faye'])

        hf = HeaderFilter.create(pk='test-hf_contact', name='Contact view', model=Contact)
        hf_items =[HeaderFilterItem.build_4_field(model=Contact, name='last_name'),
                   HeaderFilterItem.build_4_field(model=Contact, name='first_name'),
                   HeaderFilterItem.build_4_relation(rtype=rtype_pilots),
                   #TODO: build_4_customfield
                   HeaderFilterItem.build_4_functionfield(func_field=Contact.function_fields.get('get_pretty_properties')),
                  ]
        hf.set_items(hf_items)

        return hf_items

    def _set_listview_state(self):
        lv_url = Contact.get_lv_absolute_url()
        self.assertEqual(200, self.client.get(lv_url).status_code) #set the current list view state...

        return lv_url

    def test_csv_export01(self):
        self.login()
        hf_items = self._build_hf_n_contacts()
        lv_url = self._set_listview_state()

        response = self.client.get('/creme_core/list_view/dl_csv/%s' % self.ct.id, data={'list_url': lv_url})
        self.assertEqual(200, response.status_code)
        #self.assertEqual([u','.join(u'"%s"' % hfi.title for hfi in hf_items),
                          #u'"Black","Jet","Bebop",""',
                          #u'"Creme","Fulbert","",""',
                          #u'"Spiegel","Spike","Bebop/Swordfish",""',
                          #u'"Valentine","Faye","","is a girl/is beautiful"',
                          #u'"Wong","Edward","","is a girl"',
                         #],
                         #map(force_unicode, response.content.splitlines())
                        #)

        #TODO: sort the relations/properties by they verbose_name ??
        result = map(force_unicode, response.content.splitlines())
        self.assertEqual(6, len(result))
        self.assertEqual(result[0], u','.join(u'"%s"' % hfi.title for hfi in hf_items))
        self.assertEqual(result[1], u'"Black","Jet","Bebop",""')
        self.assertEqual(result[2], u'"Creme","Fulbert","",""')
        self.assertIn(result[3], (u'"Spiegel","Spike","Bebop/Swordfish",""',
                                  u'"Spiegel","Spike","Swordfish/Bebop",""')
                     )
        self.assertIn(result[4], (u'"Valentine","Faye","","is a girl/is beautiful"',
                                  u'"Valentine","Faye","","is beautiful/is a girl"')
                     )
        self.assertEqual(result[5], u'"Wong","Edward","","is a girl"')

    def test_csv_export02(self): #'export' credential
        self.login(is_superuser=False, allowed_apps=['creme_core', 'persons'])
        self._build_hf_n_contacts()
        lv_url = self._set_listview_state()

        def assertStatusCode(code):
            self.assertEqual(code,
                             self.client.get('/creme_core/list_view/dl_csv/%s' % self.ct.id,
                                             data={'list_url': lv_url},
                                            ).status_code
                            )

        assertStatusCode(403)

        self.role.exportable_ctypes = [self.ct] # set the 'export' creddential
        assertStatusCode(200)
