# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django.contrib.contenttypes.models import ContentType
    from django.urls import reverse
    from django.utils.translation import gettext as _

    from creme.creme_core.models.custom_field import CustomField, CustomFieldEnumValue
    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_models import FakeContact, FakeOrganisation
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class CustomFieldsTestCase(CremeTestCase):
    def setUp(self):
        self.login()

    def test_portal(self):
        response = self.assertGET200(reverse('creme_config__custom_fields'))
        self.assertTemplateUsed(response, 'creme_config/custom_fields_portal.html')
        self.assertEqual(reverse('creme_core__reload_bricks'),
                         response.context.get('bricks_reload_url')
                        )

    def test_add_ct01(self):
        self.assertFalse(CustomField.objects.all())

        url = reverse('creme_config__create_first_ctype_custom_field')
        context = self.assertGET200(url).context
        self.assertEqual(_('New custom field configuration'), context.get('title'))
        self.assertEqual(_('Save the custom field'),          context.get('submit_label'))

        ct = ContentType.objects.get_for_model(FakeContact)
        name = 'Size'
        field_type = CustomField.INT
        self.assertNoFormError(self.client.post(
            url,
            data={
                'content_type': ct.id,
                'name':         name,
                'field_type':   field_type,
            },
        ))

        cfields = CustomField.objects.all()
        self.assertEqual(1, len(cfields))

        cfield = cfields[0]
        self.assertEqual(ct,         cfield.content_type)
        self.assertEqual(name,       cfield.name)
        self.assertEqual(field_type, cfield.field_type)

        response = self.assertGET200(url)

        with self.assertNoException():
            ctypes = response.context['form'].fields['content_type'].ctypes

        self.assertNotIn(ct, ctypes)
        self.assertIn(ContentType.objects.get_for_model(FakeOrganisation), ctypes)

    def test_add_ct02(self):
        "Empty choice list."
        ct = ContentType.objects.get_for_model(FakeContact)
        self.assertFalse(CustomField.objects.filter(content_type=ct))

        response = self.assertPOST200(
            reverse('creme_config__create_first_ctype_custom_field'),
            data={
                'content_type': ct.id,
                'name':         'Eva',
                'field_type':   CustomField.ENUM,
                # 'enum_values': ...  #  NOPE
        })
        self.assertFormError(
            response, 'form', None,
            _('The choices list must not be empty if you choose the type "Choice list".')
        )

    def test_add_ct03(self):
        "Duplicated choices."
        response = self.assertPOST200(
            reverse('creme_config__create_first_ctype_custom_field'),
            data={
                'content_type': ContentType.objects.get_for_model(FakeContact).id,
                'name':        'Eva',
                'field_type':  CustomField.ENUM,
                'enum_values': 'Eva01\nEva02\nEva01',
            },
        )
        self.assertFormError(
            response, 'form', 'enum_values',
            _('The choice «{}» is duplicated.').format('Eva01')
        )

    def test_delete_ct(self):
        get_ct = ContentType.objects.get_for_model
        ct_contact = get_ct(FakeContact)
        ct_orga    = get_ct(FakeOrganisation)

        create_cf = CustomField.objects.create
        cfield1 = create_cf(content_type=ct_contact, name='CF#1', field_type=CustomField.INT)
        cfield2 = create_cf(content_type=ct_contact, name='CF#2', field_type=CustomField.FLOAT)
        cfield3 = create_cf(content_type=ct_orga,    name='CF#3', field_type=CustomField.BOOL)
        self.assertPOST200(reverse('creme_config__delete_ctype_custom_fields'), data={'id': ct_contact.id})
        self.assertFalse(CustomField.objects.filter(pk__in=[cfield1.pk, cfield2.pk]))
        self.assertStillExists(cfield3)

    def test_add01(self):
        get_ct = ContentType.objects.get_for_model
        contact_ct = get_ct(FakeContact)
        orga_ct    = get_ct(FakeOrganisation)

        name = 'Eva'
        create_cf = CustomField.objects.create
        create_cf(content_type=contact_ct, field_type=CustomField.BOOL, name='Operational ?')
        create_cf(content_type=orga_ct,    field_type=CustomField.INT,  name=name)  # <= same name but not same CT

        url = reverse('creme_config__create_custom_field', args=(contact_ct.id,))
        context = self.assertGET200(url).context
        self.assertEqual(_('New custom field for «{model}»').format(model='Test Contact'),
                         context.get('title')
                        )
        self.assertEqual(_('Save the custom field'), context.get('submit_label'))

        field_type = CustomField.ENUM
        self.assertNoFormError(self.client.post(
            url,
            data={
                'name':        name,
                'field_type':  field_type,
                'enum_values': 'Eva01\nEva02\nEva03',
            },
        ))

        cfields = CustomField.objects.filter(content_type=contact_ct).order_by('id')
        self.assertEqual(2, len(cfields))

        cfield2 = cfields[1]
        self.assertEqual(name,       cfield2.name)
        self.assertEqual(field_type, cfield2.field_type)
        self.assertEqual(
            ['Eva01', 'Eva02', 'Eva03'],
            [cfev.value
                for cfev in CustomFieldEnumValue.objects
                                                .filter(custom_field=cfield2)
                                                .order_by('id')
            ]
        )

    def test_add02(self):
        "content_type + name => unique together."
        ct = ContentType.objects.get_for_model(FakeContact)
        name = 'Rating'
        CustomField.objects.create(content_type=ct, name=name, field_type=CustomField.FLOAT)

        field_type = CustomField.INT
        response = self.assertPOST200(
            reverse('creme_config__create_custom_field', args=(ct.id,)),
            data={
                'name':       name,
                'field_type': field_type,
            },
        )
        self.assertFormError(
            response, 'form', 'name',
            _('There is already a custom field with this name.')
        )

    def test_add03(self):
        "Empty list of choices."
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        response = self.assertPOST200(
            reverse('creme_config__create_custom_field', args=(contact_ct.id,)),
            data={
                'name':        'Eva',
                'field_type':  CustomField.ENUM,
                'enum_values': '',
            }
        )
        self.assertFormError(
            response, 'form', None,
            _('The choices list must not be empty if you choose the type "Choice list".')
        )

    def test_add04(self):
        "Duplicated choices."
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        response = self.assertPOST200(
            reverse('creme_config__create_custom_field', args=(contact_ct.id,)),
            data={
                'name':        'Eva',
                'field_type':  CustomField.ENUM,
                'enum_values': 'Eva01\nEva02\nEva01',
            }
        )
        self.assertFormError(
            response, 'form', 'enum_values',
            _('The choice «{}» is duplicated.').format('Eva01')
        )

    def test_edit01(self):
        ct = ContentType.objects.get_for_model(FakeContact)
        name = 'nickname'
        cfield = CustomField.objects.create(content_type=ct, name=name, field_type=CustomField.STR)

        url = reverse('creme_config__edit_custom_field', args=(cfield.id,))
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/edit-popup.html')

        context = response.context
        self.assertEqual(_('Edit «{object}»').format(object=cfield), context.get('title'))

        # ---
        name = name.title()
        self.assertNoFormError(self.client.post(url, data={'name': name}))
        self.assertEqual(name, self.refresh(cfield).name)

    def test_edit02(self):
        "ENUM."
        ct = ContentType.objects.get_for_model(FakeContact)
        create_cfield = partial(CustomField.objects.create,
                                content_type=ct,
                                field_type=CustomField.MULTI_ENUM,
                               )
        cfield1 = create_cfield(name='Programming languages')
        cfield2 = create_cfield(name='Countries')

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield1)
        create_evalue(value='C')
        create_evalue(value='ABC')
        create_evalue(value='Java')
        create_evalue(value='Haskell', custom_field=cfield2)  # Should be ignored as dupliacte

        url = reverse('creme_config__edit_custom_field', args=(cfield1.id,))
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields
            new_choices = fields['new_choices']
            old_choices = fields['old_choices']

        self.assertFalse(new_choices.initial)
        self.assertEqual(['C', 'ABC', 'Java'], old_choices.content)

        response = self.client.post(
            url,
            data={
                'name': cfield1.name,
                'new_choices': 'C++\nHaskell',

                'old_choices_check_0': 'on',
                'old_choices_value_0': 'C',

                'old_choices_check_1': 'on',
                'old_choices_value_1': 'Python',
            },
        )
        self.assertNoFormError(response)

        self.assertEqual(
            ['C', 'Python', 'C++', 'Haskell'],
            [cfev.value
                for cfev in CustomFieldEnumValue.objects
                                                .filter(custom_field=cfield1)
                                                .order_by('id')
            ]
        )

    def test_edit03(self):
        "content_type + name => unique together."
        ct = ContentType.objects.get_for_model(FakeContact)
        name = 'Nickname'
        create_cfield = partial(CustomField.objects.create, content_type=ct, field_type=CustomField.STR)
        create_cfield(name=name)
        cfield2 = create_cfield(name='Label')

        response = self.assertPOST200(
            reverse('creme_config__edit_custom_field', args=(cfield2.id,)),
            data={'name': name},
        )
        self.assertFormError(
            response, 'form', 'name',
            _('There is already a custom field with this name.')
        )

    def test_edit04(self):
        "ENUM + duplicated choice."
        ct = ContentType.objects.get_for_model(FakeContact)
        cfield = CustomField.objects.create(content_type=ct,
                                            name='Programming languages',
                                            field_type=CustomField.MULTI_ENUM,
                                           )

        create_evalue = partial(CustomFieldEnumValue.objects.create, custom_field=cfield)
        eval01 = create_evalue(value='C')
        eval02 = create_evalue(value='Java')

        url = reverse('creme_config__edit_custom_field', args=(cfield.id,))
        data = {
            'name': cfield.name,
            'new_choices': f'C++\n{eval01.value}',

            'old_choices_check_0': 'on',
            'old_choices_value_0': eval01.value,

            'old_choices_check_1': 'on',
            'old_choices_value_1': eval02.value,
        }

        response1 = self.assertPOST200(url, data=data)
        self.assertFormError(
            response1, 'form', 'new_choices',
            _('The choice «{}» is duplicated.').format(eval01.value)
        )

        response2 = self.assertPOST200(
            url,
            data={
                **data,
                'new_choices': 'Ocaml\nErlang\nOcaml',
            },
        )
        self.assertFormError(
            response2, 'form', 'new_choices',
            _('The choice «{}» is duplicated.').format('Ocaml')
        )

        response3 = self.client.post(
            url,
            data={
                **data,
                # No duplicate because we renamed this previous choice
                'old_choices_value_0': 'C99',
            },
        )
        self.assertNoFormError(response3)

    def test_delete(self):
        create_cf = partial(CustomField.objects.create,
                            content_type=ContentType.objects.get_for_model(FakeContact)
                           )
        cfield1 = create_cf(name='Day',       field_type=CustomField.DATETIME)
        cfield2 = create_cf(name='Languages', field_type=CustomField.ENUM)
        cfield3 = create_cf(name='Hobbies',   field_type=CustomField.MULTI_ENUM)

        create_evalue = CustomFieldEnumValue.objects.create
        eval1 = create_evalue(custom_field=cfield2, value='C')
        eval2 = create_evalue(custom_field=cfield2, value='Python')
        eval3 = create_evalue(custom_field=cfield3, value='Programming')
        eval4 = create_evalue(custom_field=cfield3, value='Reading')

        self.assertPOST200(reverse('creme_config__delete_custom_field'), data={'id': cfield2.id})

        self.assertStillExists(cfield1)
        self.assertStillExists(cfield3)
        self.assertDoesNotExist(cfield2)

        self.assertStillExists(eval3)
        self.assertStillExists(eval4)
        self.assertDoesNotExist(eval1)
        self.assertDoesNotExist(eval2)
