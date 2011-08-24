# -*- coding: utf-8 -*-

from django.core.serializers.json import simplejson
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType

from creme_core.models import HeaderFilter, HeaderFilterItem, CremeEntity, RelationType, CustomField
from creme_core.models.header_filter import HFI_FIELD, HFI_RELATION, HFI_CUSTOM, HFI_FUNCTION
from creme_core.tests.views.base import ViewsTestCase

from persons.models import Contact, Organisation


__all__ = ('HeaderFilterViewsTestCase', )


class HeaderFilterViewsTestCase(ViewsTestCase):
    def setUp(self):
        self.populate('creme_config')
        self.contact_ct = ContentType.objects.get_for_model(Contact)

    def _find_field_index(self, formfield, name):
        for i, (fname, fvname) in enumerate(formfield.choices):
            if fname == name:
                return i

        self.fail('No "%s" field' % name)

    def test_create01(self):
        self.login()

        ct = ContentType.objects.get_for_model(CremeEntity)
        self.assertEqual(0, HeaderFilter.objects.filter(entity_type=ct).count())

        uri = '/creme_core/header_filter/add/%s' % ct.id
        response = self.client.get(uri)
        self.assertEqual(200, response.status_code)

        try:
            form = response.context['form']
            fields_field = form.fields['fields']
        except KeyError, e:
            self.fail(str(e))

        created_index = self._find_field_index(fields_field, 'created')
        name = 'DefaultHeaderFilter'
        response = self.client.post(uri,
                                    data={
                                            'name':                            name,
                                            'fields_check_%s' % created_index: 'on',
                                            'fields_value_%s' % created_index: 'created',
                                            'fields_order_%s' % created_index: 1,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)

        hfilters = HeaderFilter.objects.filter(entity_type=ct)
        self.assertEqual(1, len(hfilters))

        hfilter = hfilters[0]
        self.assertEqual(name, hfilter.name)
        self.assert_(hfilter.user is None)

        hfitems = hfilter.header_filter_items.all()
        self.assertEqual(1, len(hfitems))

        hfitem = hfitems[0]
        self.assertEqual('created',        hfitem.name)
        self.assertEqual(1,                hfitem.order)
        self.assertEqual(HFI_FIELD,        hfitem.type)
        self.assertEqual('created__range', hfitem.filter_string)
        self.failIf(hfitem.is_hidden)

    def test_create02(self):
        self.login()

        loves, loved = RelationType.create(('test-subject_love', u'Is loving'), ('test-object_love',  u'Is loved by'))
        customfield = CustomField.objects.create(name=u'Size (cm)', field_type=CustomField.INT, content_type=self.contact_ct)
        prop_funcfield = Contact.function_fields.get('get_pretty_properties')

        uri = '/creme_core/header_filter/add/%s' % self.contact_ct.id
        response = self.client.get(uri)

        try:
            fields = response.context['form'].fields
            fields_field    = fields['fields']
            cfields_field   = fields['custom_fields']
            rtypes_field    = fields['relations']
            funfields_field = fields['functions']
        except KeyError, e:
            self.fail(str(e))

        field_name = 'first_name'
        firstname_index = self._find_field_index(fields_field, field_name)
        cfield_index    = self._find_field_index(cfields_field, customfield.id)
        loves_index     = self._find_field_index(rtypes_field, loves.id)
        propfunc_index  = self._find_field_index(funfields_field, prop_funcfield.name)
        name = 'DefaultHeaderFilter'
        response = self.client.post(uri,
                                    data={
                                            'name': name,
                                            'user': self.user.id,

                                            'fields_check_%s' % firstname_index: 'on',
                                            'fields_value_%s' % firstname_index: field_name,
                                            'fields_order_%s' % firstname_index: 1,

                                            'custom_fields_check_%s' % cfield_index: 'on',
                                            'custom_fields_value_%s' % cfield_index: customfield.id,
                                            'custom_fields_order_%s' % cfield_index: 1,

                                            'relations_check_%s' % loves_index: 'on',
                                            'relations_value_%s' % loves_index: loves.id,
                                            'relations_order_%s' % loves_index: 1,

                                            'functions_check_%s' % loves_index: 'on',
                                            'functions_value_%s' % loves_index: prop_funcfield.name,
                                            'functions_order_%s' % loves_index: 1,
                                         }
                                   )
        self.assertNoFormError(response)

        try:
            hfilter = HeaderFilter.objects.get(name=name)
        except Exception, e:
            self.fail(str(e))

        self.assertEqual(self.user, hfilter.user)

        hfitems = hfilter.header_filter_items.all()
        self.assertEqual(4, len(hfitems))

        hfitem = hfitems[0]
        self.assertEqual(field_name, hfitem.name)
        self.assertEqual(1,          hfitem.order)
        self.assertEqual(HFI_FIELD,  hfitem.type)

        hfitem = hfitems[1]
        self.assertEqual(str(customfield.id), hfitem.name)
        self.assertEqual(2,                   hfitem.order)
        self.assertEqual(HFI_CUSTOM,          hfitem.type)

        hfitem = hfitems[2]
        self.assertEqual(str(loves.id), hfitem.name)
        self.assertEqual(3,             hfitem.order)
        self.assertEqual(HFI_RELATION,  hfitem.type)

        hfitem = hfitems[3]
        self.assertEqual(prop_funcfield.name, hfitem.name)
        self.assertEqual(4,                   hfitem.order)
        self.assertEqual(HFI_FUNCTION,        hfitem.type)

    def test_create03(self): #check app credentials
        self.login(is_superuser=False)

        uri = '/creme_core/header_filter/add/%s' % self.contact_ct.id
        self.assertEqual(404, self.client.get(uri).status_code)

        self.role.allowed_apps = ['persons']
        self.role.save()

        self.assertEqual(200, self.client.get(uri).status_code)

    def test_edit01(self): #not editable
        self.login()

        hf = HeaderFilter.create(pk='tests-hf_entity', name='Entity view', model=CremeEntity, is_custom=False)
        hf.set_items([HeaderFilterItem.build_4_field(model=CremeEntity, name='created')])

        self.assertEqual(404, self.client.get('/creme_core/header_filter/edit/%s' % hf.id).status_code)

    def test_edit02(self):
        self.login()

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view', model=Contact, is_custom=True)
        hf.set_items([HeaderFilterItem.build_4_field(model=Contact, name='first_name')])

        uri = '/creme_core/header_filter/edit/%s' % hf.id
        response = self.client.get(uri)
        self.assertEqual(200, response.status_code)

        try:
            fields_field = response.context['form'].fields['fields']
        except KeyError, e:
            self.fail(str(e))

        first_name_index  = None
        last_name_index = None
        for i, (fname, fvname) in enumerate(fields_field.choices):
            if   fname == 'first_name': first_name_index = i
            elif fname == 'last_name':  last_name_index  = i

        if first_name_index is None: self.fail('No "first_name" field')
        if last_name_index  is None: self.fail('No "last_name" field')

        name = 'Entity view v2'
        response = self.client.post(uri,
                                    data={
                                            'name':                               name,
                                            'fields_check_%s' % first_name_index: 'on',
                                            'fields_value_%s' % first_name_index: 'first_name',
                                            'fields_order_%s' % first_name_index: 1,
                                            'fields_check_%s' % last_name_index:  'on',
                                            'fields_value_%s' % last_name_index:  'last_name',
                                            'fields_order_%s' % last_name_index:  2,
                                         }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(302, response.status_code)

        hf = HeaderFilter.objects.get(pk=hf.id)
        self.assertEqual(name, hf.name)

        hfitems = hf.header_filter_items.all()
        self.assertEqual(2,            len(hfitems))
        self.assertEqual('first_name', hfitems[0].name)
        self.assertEqual('last_name',  hfitems[1].name)

    def test_edit03(self): #can not edit HeaderFilter that belongs to another user
        self.login(is_superuser=False)

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view', model=Contact, is_custom=True, user=self.other_user)
        self.assertEqual(404, self.client.get('/creme_core/header_filter/edit/%s' % hf.id).status_code)

    def test_edit04(self): #user do not have the app credentials
        self.login(is_superuser=False)

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view', model=Contact, is_custom=True, user=self.user)
        self.assertEqual(404, self.client.get('/creme_core/header_filter/edit/%s' % hf.id).status_code)

    def test_delete01(self):
        self.login()

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view', model=Contact, is_custom=True)
        hf.set_items([HeaderFilterItem.build_4_field(model=Contact, name='first_name')])
        self.assertEqual(200, self.client.post('/creme_core/header_filter/delete',
                                               data={'id': hf.id}, follow=True
                                              ).status_code
                        )
        self.assertEqual(0, HeaderFilter.objects.filter(pk=hf.id).count())
        self.assertEqual(0, HeaderFilterItem.objects.filter(header_filter=hf.id).count())

    def test_delete02(self): #not custom -> undeletable
        self.login()

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view', model=Contact, is_custom=False)
        self.client.post('/creme_core/header_filter/delete', data={'id': hf.id})
        self.assertEqual(1, HeaderFilter.objects.filter(pk=hf.id).count())

    def test_delete03(self): #belongs to another user
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view', model=Contact, is_custom=True, user=self.other_user)
        self.client.post('/creme_core/header_filter/delete', data={'id': hf.id})
        self.assertEqual(1, HeaderFilter.objects.filter(pk=hf.id).count())

    def test_delete04(self): #belongs to my team -> ok
        self.login()

        my_team = User.objects.create(username='TeamTitan', is_team=True)
        my_team.teammates = [self.user]

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view', model=Contact, is_custom=True, user=my_team)
        self.assertEqual(200, self.client.post('/creme_core/header_filter/delete',
                                               data={'id': hf.id}, follow=True
                                              ).status_code
                        )
        self.assertEqual(0, HeaderFilter.objects.filter(pk=hf.id).count())

    def test_delete05(self): #belongs to a team (not mine) -> ko
        self.login(is_superuser=False)

        self.role.allowed_apps = ['persons']
        self.role.save()

        a_team = User.objects.create(username='TeamTitan', is_team=True)
        a_team.teammates = [self.other_user]

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view', model=Contact, is_custom=True, user=a_team)
        self.client.post('/creme_core/header_filter/delete', data={'id': hf.id}, follow=True)
        self.assertEqual(1, HeaderFilter.objects.filter(pk=hf.id).count())

    def test_delete06(self): #logged as super user
        self.login()

        hf = HeaderFilter.create(pk='tests-hf_contact', name='Contact view', model=Contact, is_custom=True, user=self.other_user)
        self.client.post('/creme_core/header_filter/delete', data={'id': hf.id})
        self.assertEqual(0, HeaderFilter.objects.filter(pk=hf.id).count())

    def test_hfilters_for_ctype01(self):
        self.login()

        response = self.client.get('/creme_core/header_filter/get_for_ctype/%s' % self.contact_ct.id)
        self.assertEqual(200, response.status_code)
        self.assertEqual([], simplejson.loads(response.content))

    def test_hfilters_for_ctype02(self):
        self.login()

        create_hf = HeaderFilter.create
        name01 = 'Contact view01'
        name02 = 'Contact view02'
        hf01 = create_hf(pk='tests-hf_contact01', name=name01,      model=Contact,      is_custom=False)
        hf02 = create_hf(pk='tests-hf_contact02', name=name02,      model=Contact,      is_custom=True)
        hf03 = create_hf(pk='tests-hf_orga01',    name='Orga view', model=Organisation, is_custom=True)

        response = self.client.get('/creme_core/header_filter/get_for_ctype/%s' % self.contact_ct.id)
        self.assertEqual(200, response.status_code)
        self.assertEqual([[hf01.id, name01], [hf02.id, name02]], simplejson.loads(response.content))

    def test_hfilters_for_ctype03(self):
        self.login(is_superuser=False)

        response = self.client.get('/creme_core/header_filter/get_for_ctype/%s' % self.contact_ct.id)
        self.assertEqual(403, response.status_code)
