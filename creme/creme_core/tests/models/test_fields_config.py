# -*- coding: utf-8 -*-

try:
    from json import loads as json_load, dumps as json_dump

    from django.contrib.contenttypes.models import ContentType

    from ..base import CremeTestCase
    from ..fake_forms import FakeContactForm

    from creme.creme_core.utils.meta import FieldInfo
    from creme.creme_core.global_info import set_global_info
    from creme.creme_core.models import (
        FieldsConfig,
        FakeContact, FakeOrganisation, FakeCivility, FakeSector, FakeAddress,
        FakeImage, FakeFolder, FakeDocument,
    )
except Exception as e:
    print(f'Error in <{__name__}>: {e}')


class FieldsConfigTestCase(CremeTestCase):
    def setUp(self):
        super().setUp()
        set_global_info(per_request_cache={})

    def test_create(self):  # DEPRECATED
        h_field1 = 'phone'
        h_field2 = 'mobile'
        fconf = FieldsConfig.create(FakeContact,
                                    descriptions=[(h_field1, {FieldsConfig.HIDDEN: True}),
                                                  (h_field2, {FieldsConfig.HIDDEN: True}),
                                                 ],
                                   )
        self.assertIsInstance(fconf, FieldsConfig)

        fconf = self.refresh(fconf)
        get_field = FakeContact._meta.get_field
        self.assertFalse(fconf.is_field_hidden(get_field('last_name')))
        self.assertTrue(fconf.is_field_hidden(get_field(h_field1)))
        self.assertTrue(fconf.is_field_hidden(get_field(h_field2)))

        self.assertEqual(2, len(fconf.descriptions))

    def test_create_errors(self):  # DEPRECATED
        "Invalid model."
        is_valid = FieldsConfig.is_model_valid
        self.assertTrue(is_valid(FakeContact))
        self.assertTrue(is_valid(FakeOrganisation))
        self.assertTrue(is_valid(FakeAddress))
        self.assertFalse(is_valid(FakeCivility))  # No optional field
        self.assertFalse(is_valid(FakeSector))    # Idem

        create_fc = FieldsConfig.create
        with self.assertRaises(FieldsConfig.InvalidModel):
            create_fc(FakeCivility)

        with self.assertRaises(FieldsConfig.InvalidModel):
            create_fc(FakeSector)

    def test_manager_create(self):
        h_field1 = 'phone'
        h_field2 = 'mobile'
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

        self.assertEqual(2, len(fconf.descriptions))

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
        "Field is not optional: ignored."
        h_field = 'phone'
        fconf = FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (h_field,     {FieldsConfig.HIDDEN: True}),
                ('last_name', {FieldsConfig.HIDDEN: True}),
            ],
        )

        self.assertTrue(fconf.is_field_hidden(FakeContact._meta.get_field(h_field)))
        self.assertEqual(1, len(fconf.descriptions))

    def test_manager_create_errors_03(self):
        "Invalid attribute name."
        with self.assertRaises(FieldsConfig.InvalidAttribute):
            FieldsConfig.objects.create(
                content_type=FakeContact,
                descriptions=[('phone', {'invalid': True})],
            )

    def test_manager_create_errors_04(self):
        "Invalid attribute value."
        with self.assertRaises(FieldsConfig.InvalidAttribute):
            FieldsConfig.objects.create(
                content_type=FakeContact,
                descriptions=[('phone', {FieldsConfig.HIDDEN: 5})],
            )

    def test_manager_create_errors_05(self):
        "Invalid model."
        is_valid = FieldsConfig.objects.is_model_valid
        self.assertTrue(is_valid(FakeContact))
        self.assertFalse(is_valid(FakeCivility))  # No optional field
        self.assertFalse(is_valid(FakeSector))    # Idem

        create_fc = FieldsConfig.objects.create
        with self.assertRaises(FieldsConfig.InvalidModel):
            create_fc(content_type=FakeCivility)

        with self.assertRaises(FieldsConfig.InvalidModel):
            create_fc(content_type=FakeSector)

    def test_get_4_model(self):  # DEPRECATED
        model = FakeContact
        h_field1 = 'phone'
        h_field2 = 'mobile'
        FieldsConfig.create(model,
                            descriptions=[(h_field1, {FieldsConfig.HIDDEN: True}),
                                          (h_field2, {FieldsConfig.HIDDEN: True}),
                                         ],
                           )

        with self.assertNumQueries(1):
            fc = FieldsConfig.get_4_model(model)

        is_hidden = fc.is_fieldname_hidden
        self.assertTrue(is_hidden(h_field1))
        self.assertTrue(is_hidden(h_field2))
        self.assertFalse(is_hidden('description'))

        with self.assertNumQueries(0):  # Cache
            FieldsConfig.get_4_model(model)

    def test_manager_get_for_model01(self):
        model = FakeContact
        h_field1 = 'phone'
        h_field2 = 'mobile'
        FieldsConfig.objects.create(
            content_type=model,
            descriptions=[
                (h_field1, {FieldsConfig.HIDDEN: True}),
                (h_field2, {FieldsConfig.HIDDEN: True}),
            ],
        )

        with self.assertNumQueries(1):
            fc = FieldsConfig.objects.get_for_model(model)

        is_hidden = fc.is_fieldname_hidden
        self.assertTrue(is_hidden(h_field1))
        self.assertTrue(is_hidden(h_field2))
        self.assertFalse(is_hidden('description'))
        self.assertTrue(is_hidden('unknown'))

        with self.assertNumQueries(0):  # Cache
            FieldsConfig.objects.get_for_model(model)

    def test_manager_get_for_model02(self):
        "No query for model which cannot be registered."
        ContentType.objects.get_for_model(FakeCivility)  # Fill cache if needed

        with self.assertNumQueries(0):
            fc = FieldsConfig.objects.get_for_model(FakeCivility)

        self.assertFalse([*fc.hidden_fields])

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

    def test_get_4_models(self):  # DEPRECATED
        model1 = FakeContact
        model2 = FakeOrganisation

        h_field1 = 'phone'
        h_field2 = 'url_site'

        create_fc = FieldsConfig.objects.create
        create_fc(content_type=model1, descriptions=[(h_field1, {FieldsConfig.HIDDEN: True})])
        create_fc(content_type=model2, descriptions=[(h_field2, {FieldsConfig.HIDDEN: True})])

        with self.assertNumQueries(1):
            fconfigs = FieldsConfig.get_4_models([model1, model2])

        self.assertIsInstance(fconfigs, dict)
        self.assertEqual(2, len(fconfigs))

        fc1 = fconfigs.get(model1)
        self.assertIsInstance(fc1, FieldsConfig)
        self.assertEqual(model1, fc1.content_type.model_class())
        self.assertTrue(fc1.is_fieldname_hidden(h_field1))

        self.assertTrue(fconfigs.get(model2).is_fieldname_hidden(h_field2))

        with self.assertNumQueries(0):
            FieldsConfig.get_4_models([model1, model2])

        with self.assertNumQueries(0):
            FieldsConfig.get_4_model(model1)

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
        is_valid = FieldsConfig.objects.is_model_valid
        self.assertTrue(is_valid(FakeContact))
        self.assertTrue(is_valid(FakeOrganisation))
        self.assertTrue(is_valid(FakeAddress))
        self.assertFalse(is_valid(FakeCivility))  # No optional field
        self.assertFalse(is_valid(FakeSector))    # Idem

    def _create_contact_conf(self):
        FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                ('phone',  {FieldsConfig.HIDDEN: True}),
                ('mobile', {FieldsConfig.HIDDEN: True}),
            ],
        )

    def test_form_update01(self):
        user = self.create_user()
        self._create_contact_conf()

        fields = FakeContactForm(user=user).fields
        self.assertIn('last_name', fields)
        self.assertNotIn('phone',  fields)
        self.assertNotIn('mobile', fields)

    def test_form_update02(self):
        "In view."
        user = self.login()
        self._create_contact_conf()

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
        self.assertIsNone(hitagi.mobile)

    def test_form_update03(self):
        "Field not in form."
        user = self.create_user()
        self._create_contact_conf()

        class TestFakeContactForm(FakeContactForm):
            class Meta(FakeContactForm.Meta):
                exclude = ('mobile', )

        with self.assertNoException():  # KeyError...
            fields = TestFakeContactForm(user=user).fields

        self.assertIn('last_name', fields)
        self.assertNotIn('phone',  fields)
        self.assertNotIn('mobile', fields)

    def test_descriptions_setter(self):
        "Auto-repair invalid field."
        h_field = 'phone'
        fconf = FieldsConfig.objects.create(
            content_type=FakeContact,
            descriptions=[
                (h_field,   {FieldsConfig.HIDDEN: True}),
                ('invalid', {FieldsConfig.HIDDEN: True}),
            ],
         )

        fconf = self.refresh(fconf)
        self.assertTrue(fconf.is_field_hidden(FakeContact._meta.get_field(h_field)))
        self.assertEqual(1, len(fconf.descriptions))

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

    def test_localcache_get_4_model(self):
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

    def test_localcache_get_4_models(self):
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
