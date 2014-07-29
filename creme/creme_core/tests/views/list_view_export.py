# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.utils.encoding import force_unicode
    from django.utils.formats import date_format
    from django.utils.timezone import localtime
    #from django.utils.translation import ugettext as _
    from django.utils.unittest.case import skipIf

    from creme.creme_core.core.entity_cell import (EntityCellRegularField,
            EntityCellFunctionField, EntityCellRelation)
    from creme.creme_core.models import (RelationType, Relation,
            CremePropertyType, CremeProperty, HeaderFilter)
    from creme.creme_core.tests.base import skipIfNotInstalled
    from creme.creme_core.tests.views.base import ViewsTestCase

    from creme.media_managers.models import Image

    from creme.persons.models import Contact, Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))

try:
    from creme.creme_core.utils.xlrd_utils import XlrdReader
    from creme.creme_core.registry import export_backend_registry
    XlsMissing = 'xls' not in export_backend_registry.iterkeys()
except Exception:
    XlsMissing = True

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
        self.organisations = organisations = {
                name: create_orga(name=name)
                    for name in ('Bebop', 'Swordfish')
            }

        rtype_pilots = RelationType.create(('test-subject_pilots', 'pilots'),
                                           ('test-object_pilots',  'is piloted by')
                                          )[0]

        create_ptype = CremePropertyType.create
        ptype_beautiful = create_ptype(str_pk='test-prop_beautiful', text='is beautiful')
        ptype_girl      = create_ptype(str_pk='test-prop_girl',      text='is a girl')

        create_contact = partial(Contact.objects.create, user=user)
        contacts = {first_name: create_contact(first_name=first_name, last_name=last_name)
                        for first_name, last_name in [('Spike', 'Spiegel'),
                                                      ('Jet', 'Black'),
                                                      ('Faye', 'Valentine'),
                                                      ('Edward', 'Wong')
                                                     ]
                   }

        #create_rel = partial(Relation.objects.create, user=user, type=rtype_pilots)
        create_rel = partial(Relation.objects.create, user=user, type=rtype_pilots,
                             object_entity=organisations['Bebop']
                            )
        #create_rel(subject_entity=contacts['Jet'],   object_entity=bebop)
        #create_rel(subject_entity=contacts['Spike'], object_entity=bebop)
        #create_rel(subject_entity=contacts['Spike'], object_entity=swordfish)
        create_rel(subject_entity=contacts['Jet'])
        create_rel(subject_entity=contacts['Spike'])
        create_rel(subject_entity=contacts['Spike'], object_entity=organisations['Swordfish'])

        create_prop = CremeProperty.objects.create
        create_prop(type=ptype_girl,      creme_entity=contacts['Faye'])
        create_prop(type=ptype_girl,      creme_entity=contacts['Edward'])
        create_prop(type=ptype_beautiful, creme_entity=contacts['Faye'])

        cells = [EntityCellRegularField.build(model=Contact, name='civility'),
                 EntityCellRegularField.build(model=Contact, name='last_name'),
                 EntityCellRegularField.build(model=Contact, name='first_name'),
                 EntityCellRelation(rtype=rtype_pilots),
                 #TODO: EntityCellCustomField
                 EntityCellFunctionField(func_field=Contact.function_fields.get('get_pretty_properties')),
               ]
        HeaderFilter.create(pk='test-hf_contact', name='Contact view',
                            model=Contact, cells_desc=cells,
                           )

        return cells

    def _build_url(self, ct, method='download', doc_type='csv'):
        return '/creme_core/list_view/%s/%s/%s' % (method, ct.id, doc_type)

    def _set_listview_state(self, model=Contact):
        lv_url = model.get_lv_absolute_url()
        self.assertGET200(lv_url) #set the current list view state...

        return lv_url

    def test_export_error01(self):
        "Assert doc_type in ('xls', 'csv')"
        self.login()
        lv_url = self._set_listview_state()

        self.assertGET404(self._build_url(self.ct, doc_type='exe'), data={'list_url': lv_url})

    def test_list_view_export_header(self):
        self.login()
        cells = self._build_hf_n_contacts()
        lv_url = self._set_listview_state()
        url = self._build_url(self.ct, method='download_header')
        response = self.assertGET200(url, data={'list_url': lv_url})

        self.assertEqual([u','.join(u'"%s"' % hfi.title for hfi in cells)],
                         [force_unicode(line) for line in response.content.splitlines()]
                        )

    @skipIf(XlsMissing, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_xls_export_header(self):
        self.login()
        cells = self._build_hf_n_contacts()
        lv_url = self._set_listview_state()

        response = self.assertGET200(self._build_url(self.ct, method='download_header', doc_type='xls'),
                                     data={'list_url': lv_url}, follow=True
                                    )

        result = list(XlrdReader(None, file_contents=response.content))
        self.assertEqual(1, len(result))
        self.assertEqual(result[0], [hfi.title for hfi in cells])

    def test_list_view_export01(self):
        "csv"
        self.login()
        cells = self._build_hf_n_contacts()
        lv_url = self._set_listview_state()

        response = self.assertGET200(self._build_url(self.ct), data={'list_url': lv_url})

        #TODO: sort the relations/properties by they verbose_name ??
        it = (force_unicode(line) for line in response.content.splitlines())
        self.assertEqual(it.next(), u','.join(u'"%s"' % hfi.title for hfi in cells))
        self.assertEqual(it.next(), u'"","Black","Jet","Bebop",""')
        self.assertEqual(it.next(), u'"","Bouquet","Mireille","",""')
        #self.assertEqual(it.next(), u'"%s","Creme","Fulbert","",""' % _(u'Mister'))
        self.assertEqual(it.next(), u'"","Creme","Fulbert","",""')
        self.assertIn(it.next(), (u'"","Spiegel","Spike","Bebop/Swordfish",""',
                                  u'"","Spiegel","Spike","Swordfish/Bebop",""')
                     )
        self.assertIn(it.next(), (u'"","Valentine","Faye","","is a girl/is beautiful"',
                                  u'"","Valentine","Faye","","is beautiful/is a girl"')
                     )
        self.assertEqual(it.next(), u'"","Wong","Edward","","is a girl"')
        self.assertEqual(it.next(), u'"","Yumura","Kirika","",""')
        self.assertRaises(StopIteration, it.next)

    def test_list_view_export02(self):
        "scsv"
        self.login()
        cells = self._build_hf_n_contacts()
        lv_url = self._set_listview_state()

        response = self.assertGET200(self._build_url(self.ct, doc_type='scsv'), data={'list_url': lv_url})

        #TODO: sort the relations/properties by they verbose_name ??
        it = (force_unicode(line) for line in response.content.splitlines())
        self.assertEqual(it.next(), u';'.join(u'"%s"' % hfi.title for hfi in cells))
        self.assertEqual(it.next(), u'"";"Black";"Jet";"Bebop";""')
        self.assertEqual(it.next(), u'"";"Bouquet";"Mireille";"";""')
        #self.assertEqual(it.next(), u'"%s";"Creme";"Fulbert";"";""' % _('Mister'))
        self.assertEqual(it.next(), u'"";"Creme";"Fulbert";"";""')
        self.assertIn(it.next(), (u'"";"Spiegel";"Spike";"Bebop/Swordfish";""',
                                  u'"";"Spiegel";"Spike";"Swordfish/Bebop";""')
                     )
        self.assertIn(it.next(), (u'"";"Valentine";"Faye";"";"is a girl/is beautiful"',
                                  u'"";"Valentine";"Faye";"";"is beautiful/is a girl"')
                     )
        self.assertEqual(it.next(), u'"";"Wong";"Edward";"";"is a girl"')
        self.assertEqual(it.next(), u'"";"Yumura";"Kirika";"";""')
        self.assertRaises(StopIteration, it.next)

    def test_list_view_export03(self):
        "'export' credential"
        self.login(is_superuser=False, allowed_apps=['creme_core', 'persons'])
        self._build_hf_n_contacts()
        url = self._build_url(self.ct)
        data = {'list_url': self._set_listview_state()}
        self.assertGET403(url, data=data)

        self.role.exportable_ctypes = [self.ct] # set the 'export' credentials
        self.assertGET200(url, data=data)

    def test_list_view_export04(self):
        "Credential"
        self.login(is_superuser=False, allowed_apps=['creme_core', 'persons'])
        self.role.exportable_ctypes = [self.ct]

        self._build_hf_n_contacts()

        organisations = self.organisations
        bebop = organisations['Bebop']
        bebop.user = self.other_user
        bebop.save()
        self.assertFalse(self.user.has_perm_to_view(bebop))
        self.assertTrue(self.user.has_perm_to_view(organisations['Swordfish']))

        response = self.assertGET200(self._build_url(self.ct),
                                     data={'list_url': self._set_listview_state()}
                                    )
        result = map(force_unicode, response.content.splitlines())
        self.assertEqual(6, len(result)) #Fulbert & Kirika are not viewable
        self.assertEqual(result[1], '"","Black","Jet","",""')
        self.assertEqual(result[2], '"","Bouquet","Mireille","",""')
        self.assertEqual(result[3], '"","Spiegel","Spike","Swordfish",""')

    def test_list_view_export05(self):
        "Datetime field"
        self.login()

        HeaderFilter.create(pk='test-hf_contact', name='Contact view', model=Contact,
                            cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                        (EntityCellRegularField, {'name': 'created'}),
                                       ],
                           )

        lv_url = self._set_listview_state()
        response = self.assertGET200(self._build_url(self.ct), data={'list_url': lv_url})
        #result = [force_unicode(line) for line in response.content.splitlines()]
        result = [force_unicode(line) for line in response.content.splitlines()]
        self.assertEqual(4, len(result))

        #fulbert = Contact.objects.get(last_name='Creme')

        #self.assertEqual(result[1],
                         #u'"Creme","%s"' % date_format(localtime(fulbert.created), 'DATETIME_FORMAT')
                        #)
        mireille = self.other_user.linked_contact
        self.assertEqual(result[1],
                         u'"%s","%s"' % (mireille.last_name,
                                         date_format(localtime(mireille.created), 'DATETIME_FORMAT'),
                                        )
                        )

    def test_list_view_export06(self):
        "FK field on CremeEntity"
        self.login(is_superuser=False, allowed_apps=['creme_core', 'persons', 'media_managers'])
        self.role.exportable_ctypes = [self.ct]

        user = self.user

        create_img = Image.objects.create
        spike_face = create_img(name='Spike face', user=self.other_user, description="Spike's selfie")
        jet_face   = create_img(name='Jet face',   user=user,            description="Jet's selfie")
        self.assertTrue(user.has_perm_to_view(jet_face))
        self.assertFalse(user.has_perm_to_view(spike_face))

        create_contact = partial(Contact.objects.create, user=user)
        create_contact(first_name='Spike', last_name='Spiegel', image=spike_face)
        create_contact(first_name='Jet',   last_name='Black',   image=jet_face)
        create_contact(first_name='Faye',  last_name='Valentine')

        HeaderFilter.create(pk='test-hf_contact', name='Contact view', model=Contact,
                            cells_desc=[(EntityCellRegularField, {'name': 'last_name'}),
                                        (EntityCellRegularField, {'name': 'image'}),
                                        (EntityCellRegularField, {'name': 'image__description'}),
                                       ],
                           )

        lv_url = self._set_listview_state()
        response = self.assertGET200(self._build_url(self.ct), data={'list_url': lv_url})
        it = (force_unicode(line) for line in response.content.splitlines()); it.next()

        self.assertEqual(it.next(), '"Black","Jet face","Jet\'s selfie"')
        self.assertEqual(it.next(), '"Bouquet","",""')

        HIDDEN_VALUE = settings.HIDDEN_VALUE
        self.assertEqual(it.next(), '"Spiegel","%s","%s"' % (HIDDEN_VALUE, HIDDEN_VALUE))
        self.assertEqual(it.next(), '"Valentine","",""')

    @skipIfNotInstalled('creme.emails')
    def test_list_view_export07(self):
        "M2M field on CremeEntities"
        from creme.emails.models import EmailCampaign, MailingList

        self.login()

        create_camp = partial(EmailCampaign.objects.create, user=self.user)
        camp1 = create_camp(name='Camp#1')
        camp2 = create_camp(name='Camp#2')
        create_camp(name='Camp#3')

        create_ml = partial(MailingList.objects.create, user=self.user)
        camp1.mailing_lists = [create_ml(name='ML#1'), create_ml(name='ML#2')]
        camp2.mailing_lists = [create_ml(name='ML#3')]

        HeaderFilter.create(pk='test_hf', name='Campaign view', model=EmailCampaign,
                            cells_desc=[(EntityCellRegularField, {'name': 'name'}),
                                        (EntityCellRegularField, {'name': 'mailing_lists__name'}),
                                       ],
                           )

        lv_url = self._set_listview_state(model=EmailCampaign)
        response = self.assertGET200(self._build_url(ContentType.objects.get_for_model(EmailCampaign)),
                                     data={'list_url': lv_url}
                                    )
        result = [force_unicode(line) for line in response.content.splitlines()]
        self.assertEqual(4, len(result))

        self.assertEqual(result[1], '"Camp#1","ML#1/ML#2"')
        self.assertEqual(result[2], '"Camp#2","ML#3"')
        self.assertEqual(result[3], '"Camp#3",""')

    @skipIf(XlsMissing, "Skip tests, couldn't find xlwt or xlrd libs")
    def test_xls_export01(self):
        self.login()
        cells = self._build_hf_n_contacts()
        lv_url = self._set_listview_state()
        response = self.assertGET200(self._build_url(self.ct, doc_type='xls'),
                                     data={'list_url': lv_url}, follow=True,
                                    )

        it = iter(XlrdReader(None, file_contents=response.content))
        self.assertEqual(it.next(), [hfi.title for hfi in cells])
        self.assertEqual(it.next(), ["", "Black", "Jet", "Bebop", ""])
        self.assertEqual(it.next(), ["", "Bouquet", "Mireille", "", ""])
        #self.assertEqual(it.next(), [_('Mister'), "Creme", "Fulbert", "", ""])
        self.assertEqual(it.next(), ["", "Creme", "Fulbert", "", ""])
        self.assertIn(it.next(), (["", "Spiegel", "Spike", "Bebop/Swordfish", ""],
                                  ["", "Spiegel", "Spike", "Swordfish/Bebop", ""]))
        self.assertIn(it.next(), (["", "Valentine", "Faye", "", "is a girl/is beautiful"],
                                  ["", "Valentine", "Faye", "", "is beautiful/is a girl"]))
        self.assertEqual(it.next(), ["", "Wong", "Edward", "", "is a girl"])
        self.assertEqual(it.next(), ["", "Yumura", "Kirika", "", ""])
        self.assertRaises(StopIteration, it.next)
