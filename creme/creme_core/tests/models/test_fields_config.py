# -*- coding: utf-8 -*-
from io import StringIO
from json import dumps as json_dump
from json import loads as json_load

from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.core.exceptions import ValidationError
from django.forms import CharField
from django.utils.translation import gettext as _

from creme.creme_core.global_info import set_global_info
from creme.creme_core.models import (
    FakeAddress,
    FakeCivility,
    FakeContact,
    FakeDocument,
    FakeFolder,
    FakeImage,
    FakeInvoice,
    FakeOrganisation,
    FakeSector,
    FieldsConfig,
)
from creme.creme_core.utils.meta import FieldInfo

from ..base import CremeTestCase
from ..fake_forms import FakeContactForm


class FieldsConfigTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        set_global_info(per_request_cache={})

    # def test_create(self):  # DEPRECATED
    #     h_field1 = 'phone'
    #     h_field2 = 'mobile'
    #     fconf = FieldsConfig.create(FakeContact,
    #                                 descriptions=[(h_field1, {FieldsConfig.HIDDEN: True}),
    #                                               (h_field2, {FieldsConfig.HIDDEN: True}),
    #                                              ],
    #                                )
    #     self.assertIsInstance(fconf, FieldsConfig)
    #
    #     fconf = self.refresh(fconf)
    #     get_field = FakeContact._meta.get_field
    #     self.assertFalse(fconf.is_field_hidden(get_field('last_name')))
    #     self.assertTrue(fconf.is_field_hidden(get_field(h_field1)))
    #     self.assertTrue(fconf.is_field_hidden(get_field(h_field2)))
    #
    #     self.assertEqual(2, len(fconf.descriptions))

    # def test_create_errors(self):  # DEPRECATED
    #     "Invalid model."
    #     is_valid = FieldsConfig.is_model_valid
    #     self.assertTrue(is_valid(FakeContact))
    #     self.assertTrue(is_valid(FakeOrganisation))
    #     self.assertTrue(is_valid(FakeAddress))
    #     self.assertFalse(is_valid(FakeCivility))  # No optional field
    #     self.assertFalse(is_valid(FakeSector))    # Idem
    #
    #     create_fc = FieldsConfig.create
    #     with self.assertRaises(FieldsConfig.InvalidModel):
    #         create_fc(FakeCivility)
    #
    #     with self.assertRaises(FieldsConfig.InvalidModel):
    #         create_fc(FakeSector)

    def test_manager_configurable_fields01(self):
        conf_fields = {
            field.name: {*values}
            for field, values in FieldsConfig.objects.configurable_fields(FakeContact)
        }
        self.assertEqual({FieldsConfig.REQUIRED}, conf_fields.get('email'))
        self.assertEqual(
            {FieldsConfig.REQUIRED, FieldsConfig.HIDDEN},
            conf_fields.get('phone'),
        )

        # Not optional, M2M cannot be required at the moment
        self.assertNotIn('languages', conf_fields)

        self.assertNotIn('address',         conf_fields)
        self.assertNotIn('is_user',         conf_fields)  # not editable
        self.assertNotIn('cremeentity_ptr', conf_fields)  # not viewable
        self.assertNotIn('is_deleted',      conf_fields)  # not viewable
        self.assertNotIn('user',            conf_fields)  # empty
        self.assertNotIn('is_a_nerd',       conf_fields)  # BooleanField

    def test_manager_configurable_fields02(self):
        conf_fields = {
            field.name: {*values}
            for field, values in FieldsConfig.objects.configurable_fields(FakeDocument)
        }
        self.assertEqual({FieldsConfig.HIDDEN}, conf_fields.get('filedata'))

        # Not REQUIRED for M2M
        self.assertTrue(FakeDocument._meta.get_field('categories').blank)
        self.assertEqual({FieldsConfig.HIDDEN}, conf_fields.get('categories'))

    def test_manager_configurable_fields03(self):
        "Not editable fields can be hidden (but not set required)."
        conf_fields = {
            field.name: {*values}
            for field, values in FieldsConfig.objects.configurable_fields(FakeInvoice)
        }
        self.assertEqual(
            {FieldsConfig.REQUIRED, FieldsConfig.HIDDEN},
            conf_fields.get('expiration_date'),
        )
        self.assertNotIn('total_vat', conf_fields)  # Not editable, not optional

        # Optional but not editable
        self.assertEqual({FieldsConfig.HIDDEN}, conf_fields.get('total_no_vat'))

    def test_manager_create01(self):
        "HIDDEN."
        h_field1 = 'mobile'
        h_field2 = 'phone'
        fconf = FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (h_field1, {FieldsConfig.HIDDEN: True}),
                (h_field2, {FieldsConfig.HIDDEN: True}),
            ],
        )
        self.assertIsInstance(fconf, FieldsConfig)

        fconf = self.refresh(fconf)
        get_field = FakeContact._meta.get_field
        self.assertFalse(fconf.is_field_hidden(get_field('last_name')))
        self.assertTrue(fconf.is_field_hidden(get_field(h_field1)))
        self.assertTrue(fconf.is_field_hidden(get_field(h_field2)))

        self.assertListEqual(
            [
                (h_field1, {FieldsConfig.HIDDEN: True}),
                (h_field2, {FieldsConfig.HIDDEN: True}),
            ],
            fconf.descriptions,
        )

    def test_manager_create02(self):
        "REQUIRED."
        r_field1 = 'phone'
        r_field2 = 'email'
        fconf = FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (r_field1, {FieldsConfig.REQUIRED: True}),
                (r_field2, {FieldsConfig.REQUIRED: True}),
            ],
        )
        self.assertIsInstance(fconf, FieldsConfig)

        fconf = self.refresh(fconf)

        get_field = FakeContact._meta.get_field
        is_field_required = fconf.is_field_required
        self.assertTrue(is_field_required(get_field('last_name')))
        self.assertTrue(is_field_required(get_field(r_field1)))
        self.assertTrue(is_field_required(get_field(r_field2)))
        self.assertFalse(is_field_required(get_field('mobile')))
        self.assertFalse(is_field_required(get_field('is_a_nerd')))  # BooleanField

        is_fieldname_required = fconf.is_fieldname_required
        self.assertTrue(is_fieldname_required('last_name'))
        self.assertTrue(is_fieldname_required(r_field1))
        self.assertTrue(is_fieldname_required(r_field2))
        self.assertFalse(is_fieldname_required('mobile'))
        self.assertFalse(is_fieldname_required('is_a_nerd'))

        # NB: sorted by field name
        self.assertListEqual(
            [
                (r_field2, {FieldsConfig.REQUIRED: True}),
                (r_field1, {FieldsConfig.REQUIRED: True}),
            ],
            fconf.descriptions,
        )

    def test_manager_create_errors_01(self):
        "Invalid field: ignored."
        h_field = 'phone'
        fconf = FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (h_field,   {FieldsConfig.HIDDEN: True}),
                ('invalid', {FieldsConfig.HIDDEN: True}),
            ],
        )

        self.assertTrue(fconf.is_field_hidden(FakeContact._meta.get_field(h_field)))
        self.assertEqual(1, len(fconf.descriptions))

    def test_manager_create_errors_02(self):
        "Invalid attribute name."
        with self.assertRaises(FieldsConfig.InvalidAttribute):
            FieldsConfig.objects.create(
                content_type=FakeContact,
                descriptions=[('phone', {'invalid': True})],
            )

    def test_manager_create_errors_03(self):
        "Invalid attribute value."
        with self.assertRaises(FieldsConfig.InvalidAttribute):
            FieldsConfig.objects.create(
                content_type=FakeContact,
                descriptions=[('phone', {FieldsConfig.HIDDEN: 5})],
            )

    def test_manager_create_errors_04(self):
        "Field is not viewable."
        fname = 'id'

        with self.assertLogs(level='WARNING') as logs_manager:
            fconf = FieldsConfig.objects.create(
                content_type=FakeContact,
                descriptions=[(fname, {FieldsConfig.HIDDEN: True})],
            )

        self.assertFalse(fconf.descriptions)
        self.assertListEqual(
            [
                f'WARNING:creme.creme_core.models.fields_config:FieldsConfig: '
                f'the field "{fname}" is not viewable'
            ],
            logs_manager.output,
        )

    def test_manager_create_errors_hidden(self):
        "Field to hide is not optional: ignored."
        optional_field = 'phone'
        not_optional_field = 'last_name'

        with self.assertLogs(level='WARNING') as logs_manager:
            fconf = FieldsConfig.objects.create(
                content_type=FakeContact,
                descriptions=[
                    (optional_field,     {FieldsConfig.HIDDEN: True}),
                    (not_optional_field, {FieldsConfig.HIDDEN: True}),
                ],
            )

        self.assertTrue(fconf.is_fieldname_hidden(optional_field))
        self.assertEqual(1, len(fconf.descriptions))

        self.assertListEqual(
            [
                f'WARNING:creme.creme_core.models.fields_config:FieldsConfig: '
                f'the field "{not_optional_field}" is not optional'
            ],
            logs_manager.output,
        )

    def test_manager_create_errors_required01(self):
        "Field is already required: ignored."
        required_field = 'last_name'
        blank_field = 'phone'

        with self.assertLogs(level='WARNING') as logs_manager:
            fconf = FieldsConfig.objects.create(
                content_type=FakeContact,
                descriptions=[
                    (required_field, {FieldsConfig.REQUIRED: True}),
                    (blank_field, {FieldsConfig.REQUIRED: True}),
                ],
            )

        self.assertEqual(1, len(fconf.descriptions))
        self.assertTrue(fconf.is_fieldname_required(required_field))
        self.assertTrue(fconf.is_fieldname_required(blank_field))

        self.assertListEqual(
            [
                f'WARNING:creme.creme_core.models.fields_config:FieldsConfig: '
                f'the field "{required_field}" is not blank'
            ],
            logs_manager.output,
        )

    def test_manager_create_errors_required02(self):
        "Field is not editable."
        fname = 'address'

        with self.assertLogs(level='WARNING') as logs_manager:
            fconf = FieldsConfig.objects.create(
                content_type=FakeContact,
                descriptions=[(fname, {FieldsConfig.REQUIRED: True})],
            )

        self.assertFalse(fconf.descriptions)
        self.assertListEqual(
            [
                f'WARNING:creme.creme_core.models.fields_config:FieldsConfig: '
                f'the field "{fname}" is not editable'
            ],
            logs_manager.output,
        )

    def test_manager_create_errors_required03(self):
        "Field is a ManyToManyField."
        fname = 'categories'

        with self.assertLogs(level='WARNING') as logs_manager:
            fconf = FieldsConfig.objects.create(
                content_type=FakeDocument,
                descriptions=[(fname, {FieldsConfig.REQUIRED: True})],
            )

        self.assertFalse(fconf.descriptions)
        self.assertListEqual(
            [
                f'WARNING:creme.creme_core.models.fields_config:FieldsConfig: '
                f'the field "{fname}" is a ManyToManyField & cannot be required'
            ],
            logs_manager.output,
        )

    def test_manager_create_errors_hidden_n_required(self):
        with self.assertRaises(FieldsConfig.InvalidAttribute):
            FieldsConfig.objects.create(
                content_type=FakeContact,
                descriptions=[(
                    'phone',
                    {FieldsConfig.REQUIRED: True, FieldsConfig.HIDDEN: True},
                )],
            )

    # def test_manager_create_errors_invalid_model(self):
    #     "Invalid model."
    #     is_valid = FieldsConfig.objects.is_model_valid
    #     self.assertTrue(is_valid(FakeContact))
    #     self.assertFalse(is_valid(FakeCivility))  # No optional field
    #     self.assertFalse(is_valid(FakeSector))    # Idem
    #
    #     create_fc = FieldsConfig.objects.create
    #     with self.assertRaises(FieldsConfig.InvalidModel):
    #         create_fc(content_type=FakeCivility)
    #
    #     with self.assertRaises(FieldsConfig.InvalidModel):
    #         create_fc(content_type=FakeSector)

    # def test_get_4_model(self):  # DEPRECATED
    #     model = FakeContact
    #     h_field1 = 'phone'
    #     h_field2 = 'mobile'
    #     FieldsConfig.create(model,
    #                         descriptions=[(h_field1, {FieldsConfig.HIDDEN: True}),
    #                                       (h_field2, {FieldsConfig.HIDDEN: True}),
    #                                      ],
    #                        )
    #
    #     with self.assertNumQueries(1):
    #         fc = FieldsConfig.get_4_model(model)
    #
    #     is_hidden = fc.is_fieldname_hidden
    #     self.assertTrue(is_hidden(h_field1))
    #     self.assertTrue(is_hidden(h_field2))
    #     self.assertFalse(is_hidden('description'))
    #
    #     with self.assertNumQueries(0):  # Cache
    #         FieldsConfig.get_4_model(model)

    def test_manager_get_for_model01(self):
        model = FakeContact
        h_field1 = 'phone'
        h_field2 = 'mobile'
        r_field1 = 'email'
        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[
                (h_field1, {FieldsConfig.HIDDEN: True}),
                (h_field2, {FieldsConfig.HIDDEN: True}),
                (r_field1, {FieldsConfig.REQUIRED: True}),
            ],
        )

        with self.assertNumQueries(1):
            fc = FieldsConfig.objects.get_for_model(model)

        is_hidden = fc.is_fieldname_hidden
        self.assertTrue(is_hidden(h_field1))
        self.assertTrue(is_hidden(h_field2))
        self.assertFalse(is_hidden('description'))
        self.assertTrue(is_hidden('unknown'))

        is_required = fc.is_fieldname_required
        self.assertTrue(is_required(r_field1))
        self.assertTrue(is_required('last_name'))
        self.assertFalse(is_required('first_name'))
        # self.assertFalse(is_required('unknown')) TODO ? (or test exception)

        self.assertCountEqual(
            [h_field1, h_field2],
            [field.name for field in fc.hidden_fields],
        )
        self.assertListEqual(
            [r_field1],
            [field.name for field in fc.required_fields],
        )

        with self.assertNumQueries(0):  # Cache
            FieldsConfig.objects.get_for_model(model)

    def test_manager_get_for_model02(self):
        "No query for model which cannot be registered."
        ContentType.objects.get_for_model(FakeCivility)  # Fill cache if needed

        with self.assertNumQueries(0):
            fc = FieldsConfig.objects.get_for_model(FakeCivility)

        self.assertFalse([*fc.hidden_fields])
        self.assertFalse([*fc.required_fields])

    def test_manager_get_for_model03(self):
        "Cache not created."
        model = FakeContact
        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[('phone', {FieldsConfig.HIDDEN: True})],
        )

        set_global_info(per_request_cache=None)

        with self.assertNumQueries(1):
            FieldsConfig.objects.get_for_model(model)

        with self.assertNumQueries(0):
            FieldsConfig.objects.get_for_model(model)

    # def test_get_4_models(self):  # DEPRECATED
    #     model1 = FakeContact
    #     model2 = FakeOrganisation
    #
    #     h_field1 = 'phone'
    #     h_field2 = 'url_site'
    #
    #     create_fc = FieldsConfig.objects.create
    #     create_fc(content_type=model1, descriptions=[(h_field1, {FieldsConfig.HIDDEN: True})])
    #     create_fc(content_type=model2, descriptions=[(h_field2, {FieldsConfig.HIDDEN: True})])
    #
    #     with self.assertNumQueries(1):
    #         fconfigs = FieldsConfig.get_4_models([model1, model2])
    #
    #     self.assertIsInstance(fconfigs, dict)
    #     self.assertEqual(2, len(fconfigs))
    #
    #     fc1 = fconfigs.get(model1)
    #     self.assertIsInstance(fc1, FieldsConfig)
    #     self.assertEqual(model1, fc1.content_type.model_class())
    #     self.assertTrue(fc1.is_fieldname_hidden(h_field1))
    #
    #     self.assertTrue(fconfigs.get(model2).is_fieldname_hidden(h_field2))
    #
    #     with self.assertNumQueries(0):
    #         FieldsConfig.get_4_models([model1, model2])
    #
    #     with self.assertNumQueries(0):
    #         FieldsConfig.get_4_model(model1)

    def test_manager_get_for_models(self):
        model1 = FakeContact
        model2 = FakeOrganisation

        h_field1 = 'phone'
        h_field2 = 'url_site'

        create_fc = FieldsConfig.objects.create
        create_fc(content_type=model1, descriptions=[(h_field1, {FieldsConfig.HIDDEN: True})])
        create_fc(content_type=model2, descriptions=[(h_field2, {FieldsConfig.HIDDEN: True})])

        with self.assertNumQueries(1):
            fconfigs = FieldsConfig.objects.get_for_models([model1, model2])

        self.assertIsInstance(fconfigs, dict)
        self.assertEqual(2, len(fconfigs))

        fc1 = fconfigs.get(model1)
        self.assertIsInstance(fc1, FieldsConfig)
        self.assertEqual(model1, fc1.content_type.model_class())
        self.assertTrue(fc1.is_fieldname_hidden(h_field1))

        self.assertTrue(fconfigs.get(model2).is_fieldname_hidden(h_field2))

        with self.assertNumQueries(0):
            FieldsConfig.objects.get_for_models([model1, model2])

        with self.assertNumQueries(0):
            FieldsConfig.objects.get_for_model(model1)

    def test_manager_is_model_valid(self):
        has_configurable_fields = FieldsConfig.objects.is_model_valid
        self.assertTrue(has_configurable_fields(FakeContact))
        self.assertTrue(has_configurable_fields(FakeOrganisation))
        self.assertTrue(has_configurable_fields(FakeAddress))
        self.assertFalse(has_configurable_fields(FakeCivility))  # No optional field
        self.assertFalse(has_configurable_fields(FakeSector))    # Idem

    def test_manager_has_configurable_fields(self):
        is_valid = FieldsConfig.objects.has_configurable_fields
        self.assertTrue(is_valid(FakeContact))
        self.assertTrue(is_valid(FakeOrganisation))
        self.assertTrue(is_valid(FakeAddress))
        self.assertFalse(is_valid(FakeCivility))  # No optional field
        self.assertFalse(is_valid(FakeSector))    # Idem

    def _create_contact_hidden_conf(self):
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                ('phone',  {FieldsConfig.HIDDEN: True}),
                ('mobile', {FieldsConfig.HIDDEN: True}),
            ],
        )

    def test_form_update_hidden01(self):
        user = self.create_user()
        self._create_contact_hidden_conf()

        fields = FakeContactForm(user=user).fields
        self.assertIn('last_name', fields)
        self.assertNotIn('phone',  fields)
        self.assertNotIn('mobile', fields)

    def test_form_update_hidden02(self):
        "In view."
        user = self.login()
        self._create_contact_hidden_conf()

        url = '/tests/contact/add'
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertIn('last_name', fields)
        self.assertNotIn('phone',  fields)
        self.assertNotIn('mobile', fields)

        # last_name = 'Senjōgahara' MySQL does not like this....
        last_name = 'Senjougahara'
        first_name = 'Hitagi'
        response = self.client.post(
            url, follow=True,
            data={
                'user':       user.id,
                'last_name':  last_name,
                'first_name': first_name,
                'phone':      '112233',
                'mobile':     '445566',
            },
        )
        self.assertNoFormError(response)

        hitagi = self.get_object_or_fail(FakeContact, last_name=last_name)
        self.assertEqual(first_name, hitagi.first_name)
        self.assertIsNone(hitagi.phone)
        # self.assertIsNone(hitagi.mobile)
        self.assertEqual('', hitagi.mobile)

    def test_form_update_hidden03(self):
        "Field not in form."
        user = self.create_user()
        self._create_contact_hidden_conf()

        class TestFakeContactForm(FakeContactForm):
            class Meta(FakeContactForm.Meta):
                exclude = ('mobile', )

        with self.assertNoException():  # KeyError...
            fields = TestFakeContactForm(user=user).fields

        self.assertIn('last_name', fields)
        self.assertNotIn('phone',  fields)
        self.assertNotIn('mobile', fields)

    def test_form_update_required01(self):
        user = self.create_user()

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                ('phone',  {FieldsConfig.REQUIRED: True}),
            ],
        )

        fields = FakeContactForm(user=user).fields
        self.assertFalse(fields['mobile'].required)
        self.assertTrue(fields['phone'].required)

    def test_form_update_required02(self):
        "Field not present => added."
        user = self.create_user()

        class LightFakeContactForm(FakeContactForm):
            class Meta(FakeContactForm.Meta):
                fields = ('user', 'last_name')

        required = 'first_name'
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (required,  {FieldsConfig.REQUIRED: True}),
            ],
        )

        form = LightFakeContactForm(user=user)
        first_name_f = form.fields.get(required)
        self.assertIsInstance(first_name_f, CharField)
        self.assertEqual(_('First name'), first_name_f.label)
        self.assertEqual(100,             first_name_f.max_length)
        self.assertTrue(first_name_f.required)

    def test_descriptions_setter01(self):
        "Auto-repair invalid fields."
        h_field = 'phone'
        fconf = FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (h_field,    {FieldsConfig.HIDDEN: True}),
                ('invalid1', {FieldsConfig.HIDDEN: True}),
                ('invalid2', {FieldsConfig.REQUIRED: True}),
            ],
        )

        fconf = self.refresh(fconf)
        self.assertTrue(fconf.is_field_hidden(FakeContact._meta.get_field(h_field)))
        self.assertEqual(1, len(fconf.descriptions))

    def test_descriptions_setter02(self):
        "No content type."
        with self.assertRaises(ValueError) as cm1:
            FieldsConfig(
                # content_type=FakeContact,
                descriptions=[('phone', {FieldsConfig.HIDDEN: True})],
            )

        msg = 'FieldsConfig.descriptions: the content type has not been passed or is invalid.'
        self.assertEqual(msg, str(cm1.exception))

        # ---
        fconf = FieldsConfig()
        with self.assertRaises(ValueError) as cm2:
            fconf.descriptions = [('phone', {FieldsConfig.HIDDEN: True})]

        self.assertEqual(msg, str(cm2.exception))

        # ---
        with self.assertNoException():
            FieldsConfig(
                descriptions=[('phone', {FieldsConfig.HIDDEN: True})],
                content_type=FakeContact,  # Passed after
            )

    def test_descriptions_setter03(self):
        "Invalid content type."
        ctype = ContentType(app_label='invalid', model='Contact')

        with self.assertRaises(ValueError) as cm:
            FieldsConfig(
                content_type=ctype,
                descriptions=[('phone', {FieldsConfig.HIDDEN: True})],
            )

        self.assertEqual(
            'FieldsConfig.descriptions: the content type has not been passed or is invalid.',
            str(cm.exception),
        )

    def test_descriptions_getter(self):
        "Auto-repair invalid field."
        h_field = 'phone'
        fconf = FieldsConfig.objects.create(
            content_type=FakeContact,
            raw_descriptions=json_dump([
                (h_field,   {FieldsConfig.HIDDEN: True}),
                ('invalid', {FieldsConfig.HIDDEN: True}),
            ]),
        )

        fconf = self.refresh(fconf)
        self.assertEqual(1, len(fconf.descriptions))

        fconf = self.refresh(fconf)
        self.assertEqual(1, len(json_load(fconf.raw_descriptions)))
        self.assertTrue(fconf.is_field_hidden(FakeContact._meta.get_field(h_field)))

    def test_ct_cache(self):
        model = FakeContact
        ContentType.objects.get_for_model(model)  # Ensure that ContentType is filled

        fconf = FieldsConfig.objects.create(
            content_type=model,
            descriptions=[('last_name', {FieldsConfig.HIDDEN: True})],
        )
        fconf = self.refresh(fconf)

        with self.assertNumQueries(0):
            ct = fconf.content_type

        self.assertEqual(FakeContact, ct.model_class())

    def test_localcache_get_4_model(self):  # DEPRECATED
        model1 = FakeContact
        model2 = FakeOrganisation

        h_field1 = 'phone'
        h_field2 = 'url_site'

        create_fc = FieldsConfig.objects.create
        create_fc(content_type=model1, descriptions=[(h_field1, {FieldsConfig.HIDDEN: True})])
        create_fc(content_type=model2, descriptions=[(h_field2, {FieldsConfig.HIDDEN: True})])

        lc = FieldsConfig.LocalCache()

        with self.assertNumQueries(1):
            fc1 = lc.get_4_model(model1)

        self.assertIsInstance(fc1, FieldsConfig)
        self.assertEqual(model1, fc1.content_type.model_class())
        self.assertTrue(fc1.is_fieldname_hidden(h_field1))

        with self.assertNumQueries(0):
            lc.get_4_model(model1)

        with self.assertNumQueries(1):
            fc2 = lc.get_4_model(model2)

        self.assertTrue(fc2.is_fieldname_hidden(h_field2))

    def test_localcache_get_for_model(self):
        model1 = FakeContact
        model2 = FakeOrganisation

        h_field1 = 'phone'
        h_field2 = 'url_site'

        create_fc = FieldsConfig.objects.create
        create_fc(content_type=model1, descriptions=[(h_field1, {FieldsConfig.HIDDEN: True})])
        create_fc(content_type=model2, descriptions=[(h_field2, {FieldsConfig.HIDDEN: True})])

        lc = FieldsConfig.LocalCache()

        with self.assertNumQueries(1):
            fc1 = lc.get_for_model(model1)

        self.assertIsInstance(fc1, FieldsConfig)
        self.assertEqual(model1, fc1.content_type.model_class())
        self.assertTrue(fc1.is_fieldname_hidden(h_field1))

        with self.assertNumQueries(0):
            lc.get_for_model(model1)

        with self.assertNumQueries(1):
            fc2 = lc.get_for_model(model2)

        self.assertTrue(fc2.is_fieldname_hidden(h_field2))

    def test_localcache_get_4_models(self):  # DEPRECATED
        model1 = FakeContact
        model2 = FakeOrganisation

        h_field1 = 'phone'
        h_field2 = 'url_site'

        create_fc = FieldsConfig.objects.create
        create_fc(content_type=model1, descriptions=[(h_field1, {FieldsConfig.HIDDEN: True})])
        create_fc(content_type=model2, descriptions=[(h_field2, {FieldsConfig.HIDDEN: True})])

        lc = FieldsConfig.LocalCache()
        fconfigs = lc.get_4_models([model1, model2])

        fc1 = fconfigs.get(model1)
        self.assertIsInstance(fc1, FieldsConfig)
        self.assertEqual(model1, fc1.content_type.model_class())
        self.assertTrue(fc1.is_fieldname_hidden(h_field1))

        self.assertTrue(fconfigs.get(model2).is_fieldname_hidden(h_field2))

        with self.assertNumQueries(0):
            lc.get_4_model(model1)

    def test_localcache_get_for_models(self):
        model1 = FakeContact
        model2 = FakeOrganisation

        h_field1 = 'phone'
        h_field2 = 'url_site'

        create_fc = FieldsConfig.objects.create
        create_fc(content_type=model1, descriptions=[(h_field1, {FieldsConfig.HIDDEN: True})])
        create_fc(content_type=model2, descriptions=[(h_field2, {FieldsConfig.HIDDEN: True})])

        lc = FieldsConfig.LocalCache()
        fconfigs = lc.get_for_models([model1, model2])

        fc1 = fconfigs.get(model1)
        self.assertIsInstance(fc1, FieldsConfig)
        self.assertEqual(model1, fc1.content_type.model_class())
        self.assertTrue(fc1.is_fieldname_hidden(h_field1))

        self.assertTrue(fconfigs.get(model2).is_fieldname_hidden(h_field2))

        with self.assertNumQueries(0):
            lc.get_for_model(model1)

    def test_localcache_is_fieldinfo_hidden01(self):
        "No field configured."
        is_hidden = FieldsConfig.LocalCache().is_fieldinfo_hidden
        self.assertFalse(is_hidden(FieldInfo(FakeContact, 'first_name')))
        self.assertFalse(is_hidden(FieldInfo(FakeContact, 'image')))
        self.assertFalse(is_hidden(FieldInfo(FakeContact, 'image__exif_date')))

    def test_localcache_is_fieldinfo_hidden02(self):
        "Simple field hidden."
        hidden = 'first_name'

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (hidden,  {FieldsConfig.HIDDEN: True}),
            ],
        )

        is_hidden = FieldsConfig.LocalCache().is_fieldinfo_hidden
        self.assertTrue(is_hidden(FieldInfo(FakeContact, hidden)))
        self.assertFalse(is_hidden(FieldInfo(FakeContact, 'image')))
        self.assertFalse(is_hidden(FieldInfo(FakeContact, 'image__exif_date')))

    def test_localcache_is_fieldinfo_hidden03(self):
        "FK hidden."
        hidden = 'image'

        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (hidden,  {FieldsConfig.HIDDEN: True}),
            ],
        )

        is_hidden = FieldsConfig.LocalCache().is_fieldinfo_hidden
        self.assertFalse(is_hidden(FieldInfo(FakeContact, 'first_name')))
        self.assertTrue(is_hidden(FieldInfo(FakeContact, hidden)))
        self.assertTrue(is_hidden(FieldInfo(FakeContact, f'{hidden}__exif_date')))

    def test_localcache_is_fieldinfo_hidden04(self):
        "Sub-field hidden."
        hidden = 'exif_date'

        FieldsConfig.objects.create(
            content_type=FakeImage,
            descriptions=[
                (hidden,  {FieldsConfig.HIDDEN: True}),
            ],
        )

        is_hidden = FieldsConfig.LocalCache().is_fieldinfo_hidden
        self.assertFalse(is_hidden(FieldInfo(FakeContact, 'first_name')))
        self.assertFalse(is_hidden(FieldInfo(FakeContact, 'image')))
        self.assertTrue(is_hidden(FieldInfo(FakeContact, f'image__{hidden}')))

    def test_localcache_is_fieldinfo_hidden05(self):
        "Field in CremeEntity."
        hidden = 'description'
        FieldsConfig.objects.create(
            content_type=FakeImage,
            descriptions=[(hidden, {FieldsConfig.HIDDEN: True})],
        )

        is_hidden = FieldsConfig.LocalCache().is_fieldinfo_hidden
        self.assertTrue(is_hidden(FieldInfo(FakeImage, hidden)))
        self.assertFalse(is_hidden(FieldInfo(FakeContact, 'image')))
        self.assertTrue(is_hidden(FieldInfo(FakeContact, f'image__{hidden}')))

    def test_localcache_is_fieldinfo_hidden06(self):
        "Sub-field with depth > 1."
        hidden = 'description'
        FieldsConfig.objects.create(
            content_type=FakeFolder,
            descriptions=[(hidden, {FieldsConfig.HIDDEN: True})],
        )

        is_hidden = FieldsConfig.LocalCache().is_fieldinfo_hidden
        self.assertTrue(is_hidden(FieldInfo(FakeFolder, hidden)))
        self.assertFalse(is_hidden(FieldInfo(FakeDocument, hidden)))
        self.assertFalse(is_hidden(FieldInfo(FakeDocument, 'linked_folder')))
        self.assertTrue(is_hidden(FieldInfo(FakeDocument, f'linked_folder__{hidden}')))
        self.assertFalse(is_hidden(FieldInfo(FakeDocument, 'linked_folder__parent')))
        self.assertTrue(is_hidden(FieldInfo(FakeDocument, f'linked_folder__parent__{hidden}')))

    def test_crememodel_full_clean(self):
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[('phone', {FieldsConfig.REQUIRED: True})],
        )

        contact = FakeContact(
            user=self.create_user(),
            last_name='Senjougahara',
            first_name='Hitagi',
        )

        with self.assertRaises(ValidationError):
            contact.full_clean()

    def test_natural_key(self):
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        config = FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[],
        )
        self.assertEqual(config.natural_key(), contact_ct.natural_key())

    def test_manager_get_by_natural_key(self):
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[],
        )
        self.assertIs(
            FieldsConfig.objects.get_for_model(FakeContact),
            FieldsConfig.objects.get_by_natural_key(
                *contact_ct.natural_key()
            )
        )

    def test_fieldsconfig_serialization(self):
        contact_ct = ContentType.objects.get_for_model(FakeContact)
        config = FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[],
        )
        stream = StringIO()
        serializers.serialize(
            'json',
            [config],
            use_natural_primary_keys=True,
            use_natural_foreign_keys=True,
            stream=stream,
        )
        data = json_load(stream.getvalue())
        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0]["fields"]["content_type"],
            [*contact_ct.natural_key()])
