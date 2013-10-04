# -*- coding: utf-8 -*-

try:
    from functools import partial
    from json import loads as load_json

    from django.contrib.auth.models import User
    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models import HeaderFilter, HeaderFilterItem, CremeEntity, RelationType, CustomField
    from creme.creme_core.models.header_filter import HFI_FIELD, HFI_RELATION, HFI_CUSTOM, HFI_FUNCTION
    from .base import ViewsTestCase

    from creme.persons.constants import REL_SUB_EMPLOYED_BY
    from creme.persons.models import Contact, Organisation
except Exception as e:
    print 'Error in <%s>: %s' % (__name__, e)


__all__ = ('HeaderFilterViewsTestCase', )


class HeaderFilterViewsTestCase(ViewsTestCase):
    DELETE_URL = '/creme_core/header_filter/delete'

    @classmethod
    def setUpClass(cls):
        cls.populate('creme_config', 'persons')
        cls.contact_ct = ContentType.objects.get_for_model(Contact)

        HeaderFilterItem.objects.all().delete()
        HeaderFilter.objects.all().delete()

    def _build_add_url(self, ctype):
        return '/creme_core/header_filter/add/%s' % ctype.id

    def _build_edit_url(self, hf):
        return '/creme_core/header_filter/edit/%s' % hf.id

    def _build_get4ctype_url(self, ctype):
        return '/creme_core/header_filter/get_for_ctype/%s' % ctype.id

    def test_create01(self):
        self.login()

        ct = ContentType.objects.get_for_model(CremeEntity)
        self.assertFalse(HeaderFilter.objects.filter(entity_type=ct))

        url = self._build_add_url(ct)
        self.assertGET200(url)

        name = 'DefaultHeaderFilter'
        response = self.client.post(url, data={'name':  name,
                                               'items': 'rfield-created',
                                              }
                                   )
        self.assertNoFormError(response, status=302)

        hfilters = HeaderFilter.objects.filter(entity_type=ct)
        self.assertEqual(1, len(hfilters))

        hfilter = hfilters[0]
        self.assertEqual(name, hfilter.name)
        self.assertIsNone(hfilter.user)

        hfitems = hfilter.header_filter_items.all()
        self.assertEqual(1, len(hfitems))

        hfitem = hfitems[0]
        self.assertEqual('created',        hfitem.name)
        self.assertEqual(1,                hfitem.order)
        self.assertEqual(HFI_FIELD,        hfitem.type)
        self.assertEqual('created__range', hfitem.filter_string)
        self.assertIs(hfitem.is_hidden, False)

    def test_create02(self):
        self.login()

        ct = self.contact_ct
        loves = RelationType.create(('test-subject_love', u'Is loving'),
                                    ('test-object_love',  u'Is loved by')
                                   )[0]
        customfield = CustomField.objects.create(name=u'Size (cm)',
                                                 field_type=CustomField.INT,
                                                 content_type=ct,
                                                )
        funcfield = Contact.function_fields.get('get_pretty_properties')

        url = self._build_add_url(ct)
        response = self.assertGET200(url)

        with self.assertNoException():
            items_f = response.context['form'].fields['items']

        build_4_field = partial(HeaderFilterItem.build_4_field, model=Contact)
        self.assertEqual([build_4_field(name='first_name'),
                          build_4_field(name='last_name'),
                          build_4_field(name='email'),
                          HeaderFilterItem.build_4_relation(RelationType.objects.get(pk=REL_SUB_EMPLOYED_BY))
                         ],
                         items_f.initial
                        )

        field_name = 'first_name'
        name = 'DefaultHeaderFilter'
        response = self.client.post(url, follow=True,
                                    data={'name':   name,
                                          'user':   self.user.id,
                                          'items': 'rtype-%(rtype)s,rfield-%(rfield)s,ffield-%(ffield)s,cfield-%(cfield)s' % {
                                                        'rfield': field_name,
                                                        'cfield': customfield.id,
                                                        'rtype':  loves.id,
                                                        'ffield': funcfield.name,
                                                    }
                                         }
                                   )
        self.assertNoFormError(response)

        hfilter = self.get_object_or_fail(HeaderFilter, name=name)
        self.assertEqual(self.user, hfilter.user)

        hfitems = hfilter.header_filter_items.order_by('order')
        self.assertEqual(4, len(hfitems))

        hfitem = hfitems[0]
        self.assertEqual(loves.id,      hfitem.name)
        self.assertEqual(1,             hfitem.order)
        self.assertEqual(HFI_RELATION,  hfitem.type)

        hfitem = hfitems[1]
        self.assertEqual(field_name, hfitem.name)
        self.assertEqual(2,          hfitem.order)
        self.assertEqual(HFI_FIELD,  hfitem.type)

        hfitem = hfitems[2]
        self.assertEqual(funcfield.name, hfitem.name)
        self.assertEqual(3,              hfitem.order)
        self.assertEqual(HFI_FUNCTION,   hfitem.type)

        hfitem = hfitems[3]
        self.assertEqual(str(customfield.id), hfitem.name)
        self.assertEqual(4,                   hfitem.order)
        self.assertEqual(HFI_CUSTOM,          hfitem.type)

    def test_create03(self):
        "Check app credentials"
        self.login(is_superuser=False)

        uri = self._build_add_url(self.contact_ct)
        self.assertGET404(uri)

        self.role.allowed_apps = ['persons']
        self.role.save()

        self.assertGET200(uri)

    def test_edit01(self):
        "Not editable"
        self.login()

        hf = HeaderFilter.create(pk='tests-hf_entity', name='Entity view',
                                 model=CremeEntity, is_custom=False,
                                )
        hf.set_items([HeaderFilterItem.build_4_field(model=CremeEntity, name='created')])

        self.assertGET404(self._build_edit_url(hf))

    def test_edit02(self):
        self.login()

        field1 = 'first_name'
        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True,
                                )
        hf.set_items([HeaderFilterItem.build_4_field(model=Contact, name=field1)])

        url = self._build_edit_url(hf)
        response = self.assertGET200(url)

        with self.assertNoException():
            items_f = response.context['form'].fields['items']

        self.assertEqual(hf.items, items_f.initial)

        name = 'Entity view v2'
        field2 = 'last_name'
        response = self.client.post(url, data={'name':  name,
                                               'items': 'rfield-%s,rfield-%s' % (
                                                                field1, field2,
                                                            ),
                                              }
                                   )
        self.assertNoFormError(response, status=302)

        hf = self.refresh(hf)
        self.assertEqual(name, hf.name)

        hfitems = hf.items
        self.assertEqual(2,      len(hfitems))
        self.assertEqual(field1, hfitems[0].name)
        self.assertEqual(field2, hfitems[1].name)

    def test_edit03(self):
        "Can not edit HeaderFilter that belongs to another user"
        self.login(is_superuser=False)

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True, user=self.other_user,
                                )
        self.assertGET404(self._build_edit_url(hf))

    def test_edit04(self):
        "User do not have the app credentials"
        self.login(is_superuser=False)

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True, user=self.user,
                                )
        self.assertGET404(self._build_edit_url(hf))

    def test_delete01(self):
        self.login()

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True,
                                )
        hf.set_items([HeaderFilterItem.build_4_field(model=Contact, name='first_name')])
        self.assertPOST200(self.DELETE_URL, follow=True, data={'id': hf.id})
        self.assertFalse(HeaderFilter.objects.filter(pk=hf.id).exists())
        self.assertFalse(HeaderFilterItem.objects.filter(header_filter=hf.id))

    def test_delete02(self):
        "Not custom -> undeletable"
        self.login()

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=False,
                                )
        self.client.post(self.DELETE_URL, data={'id': hf.id})
        self.get_object_or_fail(HeaderFilter, pk=hf.id)

    def test_delete03(self):
        "Belongs to another user"
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True, user=self.other_user,
                                )
        self.client.post(self.DELETE_URL, data={'id': hf.id})
        self.get_object_or_fail(HeaderFilter, pk=hf.id)

    def test_delete04(self):
        "Belongs to my team -> ok"
        self.login()

        my_team = User.objects.create(username='TeamTitan', is_team=True)
        my_team.teammates = [self.user]

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True, user=my_team,
                                )
        self.assertPOST200(self.DELETE_URL, data={'id': hf.id}, follow=True)
        self.assertFalse(HeaderFilter.objects.filter(pk=hf.id).exists())

    def test_delete05(self):
        "Belongs to a team (not mine) -> KO"
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        a_team = User.objects.create(username='TeamTitan', is_team=True)
        a_team.teammates = [self.other_user]

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True, user=a_team,
                                )
        self.client.post(self.DELETE_URL, data={'id': hf.id}, follow=True)
        self.get_object_or_fail(HeaderFilter, pk=hf.id)

    def test_delete06(self):
        "Logged as super user"
        self.login()

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view',
                                 model=Contact, is_custom=True, user=self.other_user,
                                )
        self.client.post(self.DELETE_URL, data={'id': hf.id})
        self.assertFalse(HeaderFilter.objects.filter(pk=hf.id).exists())

    def test_hfilters_for_ctype01(self):
        self.login()

        response = self.assertGET200(self._build_get4ctype_url(self.contact_ct))
        self.assertEqual([], load_json(response.content))

    def test_hfilters_for_ctype02(self):
        self.login()

        create_hf = HeaderFilter.create
        name01 = 'Contact view01'
        name02 = 'Contact view02'
        hf01 = create_hf(pk='tests-hf_contact01', name=name01,      model=Contact,      is_custom=False)
        hf02 = create_hf(pk='tests-hf_contact02', name=name02,      model=Contact,      is_custom=True)
        create_hf(pk='tests-hf_orga01',           name='Orga view', model=Organisation, is_custom=True)

        response = self.assertGET200(self._build_get4ctype_url(self.contact_ct))
        self.assertEqual([[hf01.id, name01], [hf02.id, name02]], load_json(response.content))

    def test_hfilters_for_ctype03(self):
        self.login(is_superuser=False)
        self.assertGET403(self._build_get4ctype_url(self.contact_ct))
