# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.models.custom_field import *
    from creme.creme_core.tests.base import CremeTestCase

    from creme.persons.models import Contact, Organisation
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


__all__ = ('CustomFieldsTestCase',)


class CustomFieldsTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        cls.populate('creme_core', 'creme_config')

    def setUp(self):
        self.login()

    def test_portal(self):
        self.assertGET200('/creme_config/custom_fields/portal/')

    def test_add_ct(self):
        self.assertFalse(CustomField.objects.all())

        url = '/creme_config/custom_fields/ct/add/'
        self.assertGET200(url)

        ct = ContentType.objects.get_for_model(Contact)
        name = 'Size'
        field_type = CustomField.INT
        response = self.client.post(url, data={'content_type': ct.id,
                                               'name':         name,
                                               'field_type':   field_type,
                                              }
                                   )
        self.assertNoFormError(response)

        cfields = CustomField.objects.all()
        self.assertEqual(1, len(cfields))

        cfield = cfields[0]
        self.assertEqual(ct,         cfield.content_type)
        self.assertEqual(name,       cfield.name)
        self.assertEqual(field_type, cfield.field_type)

        response = self.assertGET200(url)

        with self.assertNoException():
            #choices = response.context['form'].fields['content_type'].choices
            ctypes = response.context['form'].fields['content_type'].ctypes

        #ct_set = set(ct_id for ct_id, vname in choices)
        #self.assertNotIn(ct.id, ct_set)
        #self.assertIn(ContentType.objects.get_for_model(Organisation).id, ct_set)
        self.assertNotIn(ct, ctypes)
        self.assertIn(ContentType.objects.get_for_model(Organisation), ctypes)

        self.assertGET200('/creme_config/custom_fields/ct/%s' % ct.id)

    def test_delete_ct(self):
        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(Contact)
        ct_orga    = get_ct(Organisation)

        create_cf = CustomField.objects.create
        cfield1 = create_cf(content_type=ct_contact, name='CF#1', field_type=CustomField.INT)
        cfield2 = create_cf(content_type=ct_contact, name='CF#2', field_type=CustomField.FLOAT)
        cfield3 = create_cf(content_type=ct_orga,    name='CF#3', field_type=CustomField.BOOL)
        self.assertPOST200('/creme_config/custom_fields/ct/delete', data={'id': ct_contact.id})
        self.assertFalse(CustomField.objects.filter(pk__in=[cfield1.pk, cfield2.pk]))
        self.assertStillExists(cfield3)

    def test_add(self):
        ct = ContentType.objects.get_for_model(Contact)
        CustomField.objects.create(content_type=ct, name='CF#1', field_type=CustomField.INT)

        url = '/creme_config/custom_fields/add/%s' % ct.id
        self.assertGET200(url)

        name = 'Eva'
        field_type = CustomField.ENUM
        response = self.client.post(url, data={'name':        name,
                                               'field_type':  field_type,
                                               'enum_values': 'Eva01\nEva02\nEva03',
                                              }
                                   )
        self.assertNoFormError(response)

        cfields = CustomField.objects.filter(content_type=ct).order_by('id')
        self.assertEqual(2, len(cfields))

        cfield2 = cfields[1]
        self.assertEqual(name,       cfield2.name)
        self.assertEqual(field_type, cfield2.field_type)
        self.assertEqual([u'Eva01', u'Eva02', u'Eva03'],
                         [cfev.value 
                            for cfev in CustomFieldEnumValue.objects
                                                            .filter(custom_field=cfield2)
                                                            .order_by('id')
                         ]
                        )

    def test_edit01(self):
        ct = ContentType.objects.get_for_model(Contact)
        name = 'nickname'
        cfield = CustomField.objects.create(content_type=ct, name=name, field_type=CustomField.STR)

        url = '/creme_config/custom_fields/edit/%s' % cfield.id
        self.assertGET200(url)

        name = name.title()
        self.assertNoFormError(self.client.post(url, data={'name': name}))
        self.assertEqual(name, self.refresh(cfield).name)

    def test_edit02(self):
        "ENUM"
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
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            new_choices = fields['new_choices']
            old_choices = fields['old_choices']

        self.assertFalse(new_choices.initial)
        self.assertEqual([u'C', u'ABC', u'Java'], old_choices.content)

        response = self.client.post(url, data={'name': cfield.name,
                                               'new_choices': 'C++\nHaskell',

                                               'old_choices_check_0': 'on',
                                               'old_choices_value_0': 'C',

                                               'old_choices_check_1': 'on',
                                               'old_choices_value_1': 'Python',
                                              }
                                   )
        self.assertNoFormError(response)

        self.assertEqual([u'C', u'Python', u'C++', u'Haskell'],
                         [cfev.value 
                            for cfev in CustomFieldEnumValue.objects
                                                            .filter(custom_field=cfield)
                                                            .order_by('id')
                         ]
                        )

    def test_delete(self):
        create_cf = partial(CustomField.objects.create,
                            content_type=ContentType.objects.get_for_model(Contact)
                           )
        cfield1 = create_cf(name='Day',       field_type=CustomField.DATETIME)
        cfield2 = create_cf(name='Languages', field_type=CustomField.ENUM)
        cfield3 = create_cf(name='Hobbies',   field_type=CustomField.MULTI_ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        eval1 = create_evalue(custom_field=cfield2, value='C')
        eval2 = create_evalue(custom_field=cfield2, value='Python')
        eval3 = create_evalue(custom_field=cfield3, value='Programming')
        eval4 = create_evalue(custom_field=cfield3, value='Reading')

        self.assertPOST200('/creme_config/custom_fields/delete', data={'id': cfield2.id})

        self.assertStillExists(cfield1)
        self.assertStillExists(cfield3)
        self.assertDoesNotExist(cfield2)

        self.assertStillExists(eval3)
        self.assertStillExists(eval4)
        self.assertDoesNotExist(eval1)
        self.assertDoesNotExist(eval2)

    #TODO: (r'^custom_fields/(?P<ct_id>\d+)/reload/$', 'custom_fields.reload_block'),
