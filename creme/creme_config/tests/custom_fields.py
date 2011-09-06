# -*- coding: utf-8 -*-

try:
    from django.contrib.contenttypes.models import ContentType

    from creme_core.models.custom_field import *
    from creme_core.tests.base import CremeTestCase
    from creme_core import autodiscover

    from persons.models import Contact, Organisation
except Exception, e:
    print 'Error:', e


__all__ = ('CustomFieldsTestCase',)


class CustomFieldsTestCase(CremeTestCase):
    def setUp(self):
        self.populate('creme_core', 'creme_config')
        self.login()

    def test_portal(self):
        self.assertEqual(200, self.client.get('/creme_config/custom_fields/portal/').status_code)

    def test_add_ct(self):
        ct = ContentType.objects.get_for_model(Contact)

        self.assertEqual(0, CustomField.objects.count())

        url = '/creme_config/custom_fields/ct/add/'
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Size'
        field_type = CustomField.INT
        response = self.client.post(url, data={
                                                'content_type': ct.id,
                                                'name':         name,
                                                'field_type':   field_type,
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        cfields = CustomField.objects.all()
        self.assertEqual(1, len(cfields))

        cfield = cfields[0]
        self.assertEqual(ct,         cfield.content_type)
        self.assertEqual(name,       cfield.name)
        self.assertEqual(field_type, cfield.field_type)

        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            choices = response.context['form'].fields['content_type'].choices
        except KeyError, e:
            self.fail(str(e))

        ct_set = set(ct_id for ct_id, vname in choices)
        self.assert_(ct.id not in ct_set)
        self.assert_(ContentType.objects.get_for_model(Organisation).id in ct_set)

        self.assertEqual(200, self.client.get('/creme_config/custom_fields/ct/%s' % ct.id).status_code)

    def test_delete_ct(self):
        ct_contact = ContentType.objects.get_for_model(Contact)
        ct_orga    = ContentType.objects.get_for_model(Organisation)

        create_cf = CustomField.objects.create
        cfield1 = create_cf(content_type=ct_contact, name='CF#1', field_type=CustomField.INT)
        cfield2 = create_cf(content_type=ct_contact, name='CF#2', field_type=CustomField.FLOAT)
        cfield3 = create_cf(content_type=ct_orga,    name='CF#3', field_type=CustomField.BOOL)

        response = self.client.post('/creme_config/custom_fields/ct/delete', data={'id': ct_contact.id})
        self.assertEqual(200, response.status_code)

        self.assertEqual(0, CustomField.objects.filter(pk__in=[cfield1.pk, cfield2.pk]).count())
        self.assertEqual(1, CustomField.objects.filter(pk=cfield3.pk).count())

    def test_add(self):
        ct = ContentType.objects.get_for_model(Contact)
        cfield1 = CustomField.objects.create(content_type=ct, name='CF#1', field_type=CustomField.INT)

        url = '/creme_config/custom_fields/add/%s' % ct.id
        self.assertEqual(200, self.client.get(url).status_code)

        name = 'Eva'
        field_type = CustomField.ENUM
        response = self.client.post(url, data={
                                                'name':        name,
                                                'field_type':  field_type,
                                                'enum_values': 'Eva01\nEva02\nEva03',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        cfields = CustomField.objects.filter(content_type=ct).order_by('id')
        self.assertEqual(2, len(cfields))

        cfield2 = cfields[1]
        self.assertEqual(name,       cfield2.name)
        self.assertEqual(field_type, cfield2.field_type)
        self.assertEqual([u'Eva01', u'Eva02', u'Eva03'],
                         [cfev.value for cfev in CustomFieldEnumValue.objects.filter(custom_field=cfield2).order_by('id')]
                        )

    def test_edit01(self):
        ct = ContentType.objects.get_for_model(Contact)
        name = 'nickname'
        cfield = CustomField.objects.create(content_type=ct, name=name, field_type=CustomField.STR)

        url = '/creme_config/custom_fields/edit/%s' % cfield.id
        self.assertEqual(200, self.client.get(url).status_code)

        name = name.title()
        response = self.client.post(url, data={'name': name})
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        cfield = CustomField.objects.get(pk=cfield.pk) #refresh
        self.assertEqual(name, cfield.name)

    def test_edit02(self): #ENUM
        ct = ContentType.objects.get_for_model(Contact)
        cfield = CustomField.objects.create(content_type=ct,
                                            name='Programming languages',
                                            field_type=CustomField.MULTI_ENUM
                                           )
        create_evalue = CustomFieldEnumValue.objects.create
        create_evalue(custom_field=cfield, value='C')
        create_evalue(custom_field=cfield, value='ABC')
        create_evalue(custom_field=cfield, value='Java')

        url = '/creme_config/custom_fields/edit/%s' % cfield.id
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)

        try:
            fields = response.context['form'].fields
            new_choices = fields['new_choices']
            old_choices = fields['old_choices']
        except KeyError, e:
            self.fail(str(e))

        self.assertEqual([u'C', u'ABC', u'Java'], old_choices.content)

        response = self.client.post(url, data={
                                                'name': cfield.name,
                                                'new_choices': 'C++\nHaskell',

                                                'old_choices_check_0': 'on',
                                                'old_choices_value_0': 'C',

                                                'old_choices_check_1': 'on',
                                                'old_choices_value_1': 'Python',
                                              }
                                   )
        self.assertNoFormError(response)
        self.assertEqual(200, response.status_code)

        self.assertEqual([u'C', u'Python', u'C++', u'Haskell'],
                         [cfev.value for cfev in CustomFieldEnumValue.objects.filter(custom_field=cfield).order_by('id')]
                        )

    def test_delete(self):
        ct = ContentType.objects.get_for_model(Contact)
        cfield1 = CustomField.objects.create(content_type=ct, name='Day',       field_type=CustomField.DATE)
        cfield2 = CustomField.objects.create(content_type=ct, name='Languages', field_type=CustomField.ENUM)
        cfield3 = CustomField.objects.create(content_type=ct, name='Hobbies',   field_type=CustomField.MULTI_ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        eval1 = create_evalue(custom_field=cfield2, value='C')
        eval2 = create_evalue(custom_field=cfield2, value='Python')
        eval3 = create_evalue(custom_field=cfield3, value='Programming')
        eval4 = create_evalue(custom_field=cfield3, value='Reading')

        response = self.client.post('/creme_config/custom_fields/delete', data={'id': cfield2.id})
        self.assertEqual(200, response.status_code)

        self.assertEqual(2, CustomField.objects.filter(pk__in=[cfield1.pk, cfield3.pk]).count())
        self.assertEqual(0, CustomField.objects.filter(pk=cfield2.pk).count())

        self.assertEqual(2, CustomFieldEnumValue.objects.filter(pk__in=[eval3.pk, eval4.pk]).count())
        self.assertEqual(0, CustomFieldEnumValue.objects.filter(pk__in=[eval1.pk, eval2.pk]).count())

    #TODO: (r'^custom_fields/(?P<ct_id>\d+)/reload/$', 'custom_fields.reload_block'),
