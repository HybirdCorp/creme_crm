# -*- coding: utf-8 -*-

try:
    from functools import partial

    from django import forms
    from django.contrib.contenttypes.models import ContentType
    from django.forms.boundfield import BoundField
    from django.utils.translation import ugettext as _

    from creme.creme_core.forms import CremeForm, CremeModelForm
    from creme.creme_core.models import (CustomField, CustomFieldInteger, FieldsConfig,
            FakeContact, FakeAddress, FakeSector)

    from ..base import CremeTestCase
    from ..fake_forms import FakeContactForm
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


# TODO: test CremeModelWithUserForm
# TODO: test hooks

class CremeFormTestCase(CremeTestCase):
    def test_01(self):
        user = self.login()

        class TestCremeForm(CremeForm):
            order = forms.IntegerField(label='Order')
            description = forms.CharField(label='Description', required=False)

        form = TestCremeForm(user=user)
        self.assertEqual(user, form.fields['order'].user)

        blocks = form.get_blocks()
        with self.assertNoException():
            general_group = blocks['general']

        self.assertIsInstance(general_group, tuple)
        self.assertEqual(2, len(general_group))
        self.assertEqual(_('General information'), general_group[0])

        items = general_group[1]
        self.assertIsInstance(items, list)
        self.assertEqual(2, len(items))

        # --
        item1 = items[0]
        self.assertIsInstance(item1, tuple)
        self.assertEqual(2, len(item1))
        self.assertIs(item1[1], True)

        bound_field1 = item1[0]
        self.assertIsInstance(bound_field1, BoundField)
        self.assertEqual('order', bound_field1.name)

        # --
        item2 = items[1]
        self.assertEqual('description', item2[0].name)
        self.assertIs(item2[1], False)


class CremeModelFormTestCase(CremeTestCase):
    def test_basic(self):
        user = self.login()

        class FakeSectorForm(CremeModelForm):
            class Meta:
                model = FakeSector
                fields = '__all__'

        form2 = FakeSectorForm(user=user)
        fields = form2.fields

        with self.assertNoException():
            order_f = fields['title']

        self.assertEqual(user, order_f.user)
        self.assertIn('is_custom', fields)
        self.assertNotIn('order',  fields)

        # ---
        blocks = form2.get_blocks()
        with self.assertNoException():
            general_group = blocks['general']

        self.assertIsInstance(general_group, tuple)
        self.assertEqual(2, len(general_group))
        self.assertEqual(_('General information'), general_group[0])
        self.assertEqual(2, len(general_group[1]))

        # --
        form1 = FakeSectorForm(user=user, data={})
        self.assertFormInstanceErrors(form1, ('title', _('This field is required.')))

        # --
        title = 'IT'
        form2 = FakeSectorForm(user=user, data={'title': title})
        self.assertFalse(form2.errors)

        sector = form2.save()
        self.assertIsInstance(sector, FakeSector)
        self.assertEqual(title, sector.title)
        self.assertFalse(sector.is_custom)
        self.assertIsNotNone(sector.id)

    def test_fields_config(self):
        user = self.login()

        FieldsConfig.create(
            FakeAddress,
            descriptions=[('department', {FieldsConfig.HIDDEN: True})],
        )

        class FakeAddressForm(CremeModelForm):
            class Meta:
                model = FakeAddress
                exclude = ('zipcode', )

        fields = FakeAddressForm(user=user).fields
        self.assertIn('value', fields)
        self.assertIn('city',  fields)
        self.assertNotIn('zipcode',    fields)
        self.assertNotIn('department', fields)


class CremeEntityFormTestCase(CremeTestCase):
    def test_basic(self):
        user = self.login()

        form = FakeContactForm(user=user)
        fields = form.fields
        self.assertIn('first_name', fields)
        self.assertIn('last_name', fields)
        self.assertNotIn('is_user', fields)

        # ---
        blocks = form.get_blocks()
        with self.assertNoException():
            general_group = blocks['general']

        self.assertIsInstance(general_group, tuple)
        self.assertEqual(2, len(general_group))
        self.assertEqual(_('General information'), general_group[0])
        self.assertGreater(len(general_group[1]), 10)

        # ---
        first_name = 'Kanbaru'
        last_name = 'Suruga'
        form = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,
             },
        )
        self.assertFalse(form.errors)

        contact = form.save()
        self.assertIsInstance(contact, FakeContact)
        self.assertEqual(user,       contact.user)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(last_name,  contact.last_name)
        self.assertIsNotNone(contact.id)

    def test_customfields(self):
        user = self.login()

        create_cf = partial(
            CustomField.objects.create,
            content_type=ContentType.objects.get_for_model(FakeContact),
        )
        cfield1 = create_cf(name='Size',   field_type=CustomField.INT)
        cfield2 = create_cf(name='Cursed', field_type=CustomField.BOOL)

        fields = FakeContactForm(user=user).fields

        with self.assertNoException():
            cf_f1 = fields['custom_field_0']
            cf_f2 = fields['custom_field_1']

        self.assertIsInstance(cf_f1, forms.IntegerField)
        self.assertIsInstance(cf_f2, forms.NullBooleanField)

        # ---
        first_name = 'Karen'
        last_name = 'Araragi'
        form = FakeContactForm(
            user=user,
            data={
                'user':       user.id,
                'first_name': first_name,
                'last_name':  last_name,

                'custom_field_0': '150',
                'custom_field_1': '',
             },
        )
        self.assertFalse(form.errors)

        contact = form.save()
        self.assertIsInstance(contact, FakeContact)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(last_name,  contact.last_name)

        cf_value = self.get_object_or_fail(CustomFieldInteger,
                                           custom_field=cfield1,
                                           entity=contact,
                                          )
        self.assertEqual(150, cf_value.value)
