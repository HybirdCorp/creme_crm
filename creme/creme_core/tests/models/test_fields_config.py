# -*- coding: utf-8 -*-

try:
    from json import loads as json_loads, dumps as json_dumps

    from django.contrib.contenttypes.models import ContentType

    from ..base import CremeTestCase
    from ..fake_forms import FakeContactForm
    from ..fake_models import FakeContact, FakeOrganisation, FakeCivility, FakeAddress, FakeEmailCampaign

    from creme.creme_core.global_info import set_global_info
    from creme.creme_core.models import CremeEntity, FieldsConfig
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


class FieldsConfigTestCase(CremeTestCase):
    def setUp(self):
        super(FieldsConfigTestCase, self).setUp()
        set_global_info(per_request_cache={})

    def test_create01(self):
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

    def test_create_errors_01(self):
        "Invalid field: ignored"
        h_field = 'phone'
        fconf = FieldsConfig.create(FakeContact,
                                    descriptions=[(h_field,   {FieldsConfig.HIDDEN: True}),
                                                  ('invalid', {FieldsConfig.HIDDEN: True}),
                                                 ],
                                   )

        self.assertTrue(fconf.is_field_hidden(FakeContact._meta.get_field(h_field)))
        self.assertEqual(1, len(fconf.descriptions))

    def test_create_errors_02(self):
        "Field is not optional: ignored"
        h_field = 'phone'
        fconf = FieldsConfig.create(FakeContact,
                                    descriptions=[(h_field,     {FieldsConfig.HIDDEN: True}),
                                                  ('last_name', {FieldsConfig.HIDDEN: True}),
                                                 ],
                                   )

        self.assertTrue(fconf.is_field_hidden(FakeContact._meta.get_field(h_field)))
        self.assertEqual(1, len(fconf.descriptions))

    def test_create_errors_03(self):
        "Invalid attribute name"
        with self.assertRaises(FieldsConfig.InvalidAttribute):
            FieldsConfig.create(FakeContact, descriptions=[('phone', {'invalid': True})])

    def test_create_errors_04(self):
        "Invalid attribute value"
        with self.assertRaises(FieldsConfig.InvalidAttribute):
            FieldsConfig.create(FakeContact,
                                descriptions=[('phone', {FieldsConfig.HIDDEN: 5})],
                               )

    def test_create_errors_05(self):
        "Invalid model"
        is_valid = FieldsConfig.is_model_valid
        self.assertTrue(is_valid(FakeContact))
        self.assertTrue(is_valid(FakeOrganisation))
        self.assertTrue(is_valid(FakeAddress))
        self.assertFalse(is_valid(CremeEntity))       # No optional field
        self.assertFalse(is_valid(FakeEmailCampaign)) # Idem
        self.assertFalse(is_valid(FakeCivility))      # Idem

        create_fc = FieldsConfig.create

        with self.assertRaises(FieldsConfig.InvalidModel):
            create_fc(CremeEntity)

        with self.assertRaises(FieldsConfig.InvalidModel):
            create_fc(FakeCivility)

    def test_get_4_model01(self):
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

        with self.assertNumQueries(0): # cache
            FieldsConfig.get_4_model(model)

    def test_get_4_model02(self):
        "No query for model which cannot be registered"
        with self.assertNumQueries(0):
            fc = FieldsConfig.get_4_model(CremeEntity)

        self.assertFalse(list(fc.hidden_fields))

    def test_get_4_model03(self):
        "Cache not created"
        model = FakeContact
        FieldsConfig.create(model,
                            descriptions=[('phone', {FieldsConfig.HIDDEN: True})],
                           )

        set_global_info(per_request_cache=None)

        with self.assertNumQueries(1):
            FieldsConfig.get_4_model(model)

        with self.assertNumQueries(0):
            FieldsConfig.get_4_model(model)

    def test_get_4_models(self):
        model1 = FakeContact
        model2 = FakeOrganisation

        h_field1 = 'phone'
        h_field2 = 'url_site'

        create_fc = FieldsConfig.create
        create_fc(model1, descriptions=[(h_field1, {FieldsConfig.HIDDEN: True})])
        create_fc(model2, descriptions=[(h_field2, {FieldsConfig.HIDDEN: True})])

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

    def _create_contact_conf(self):
        FieldsConfig.create(FakeContact,
                            descriptions=[('phone',  {FieldsConfig.HIDDEN: True}),
                                          ('mobile', {FieldsConfig.HIDDEN: True}),
                                         ],
                           )

    def test_form_update01(self):
        user = self.login()
        self._create_contact_conf()

        fields = FakeContactForm(user=user).fields
        self.assertIn('last_name', fields)
        self.assertNotIn('phone',  fields)
        self.assertNotIn('mobile', fields)

    def test_form_update02(self):
        "In view"
        user = self.login()
        self._create_contact_conf()

        url = '/tests/contact/add'
        response = self.assertGET200(url)

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertIn('last_name', fields)
        self.assertNotIn('phone',  fields)
        self.assertNotIn('mobile', fields)

        # last_name = u'Senjōgahara' MySQL does not like this....
        last_name = u'Senjougahara'
        first_name = u'Hitagi'
        response = self.client.post(url, follow=True,
                                    data={'user':       user.id,
                                          'last_name':  last_name,
                                          'first_name': first_name,
                                          'phone':      '112233',
                                          'mobile':     '445566',
                                         }
                                   )
        self.assertNoFormError(response)

        hitagi = self.get_object_or_fail(FakeContact, last_name=last_name)
        self.assertEqual(first_name, hitagi.first_name)
        self.assertIsNone(hitagi.phone)
        self.assertIsNone(hitagi.mobile)

    def test_form_update03(self):
        "Field not in form"
        user = self.login()
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
        "Auto-repair invalid field"
        h_field = 'phone'
        fconf = FieldsConfig.objects.create(
                    content_type=ContentType.objects.get_for_model(FakeContact),
                    descriptions=[(h_field,   {FieldsConfig.HIDDEN: True}),
                                  ('invalid', {FieldsConfig.HIDDEN: True}),
                                 ],
                 )

        fconf = self.refresh(fconf)
        self.assertTrue(fconf.is_field_hidden(FakeContact._meta.get_field(h_field)))
        self.assertEqual(1, len(fconf.descriptions))

    def test_descriptions_getter(self):
        "Auto-repair invalid field"
        h_field = 'phone'
        fconf = FieldsConfig.objects.create(
                    content_type=ContentType.objects.get_for_model(FakeContact),
                    raw_descriptions=json_dumps([(h_field, {FieldsConfig.HIDDEN: True}),
                                                 ('invalid', {FieldsConfig.HIDDEN: True}),
                                                 ]
                                                ),
                 )

        fconf = self.refresh(fconf)
        self.assertEqual(1, len(fconf.descriptions))

        fconf = self.refresh(fconf)
        self.assertEqual(1, len(json_loads(fconf.raw_descriptions)))
        self.assertTrue(fconf.is_field_hidden(FakeContact._meta.get_field(h_field)))

    def test_ct_cache(self):
        model = FakeContact
        ContentType.objects.get_for_model(model)  # Ensure that ContentType is filled

        fconf = FieldsConfig.create(model,
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

        create_fc = FieldsConfig.create
        create_fc(model1, descriptions=[(h_field1, {FieldsConfig.HIDDEN: True})])
        create_fc(model2, descriptions=[(h_field2, {FieldsConfig.HIDDEN: True})])

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

        create_fc = FieldsConfig.create
        create_fc(model1, descriptions=[(h_field1, {FieldsConfig.HIDDEN: True})])
        create_fc(model2, descriptions=[(h_field2, {FieldsConfig.HIDDEN: True})])

        lc = FieldsConfig.LocalCache()
        fconfigs = lc.get_4_models([model1, model2])

        fc1 = fconfigs.get(model1)
        self.assertIsInstance(fc1, FieldsConfig)
        self.assertEqual(model1, fc1.content_type.model_class())
        self.assertTrue(fc1.is_fieldname_hidden(h_field1))

        self.assertTrue(fconfigs.get(model2).is_fieldname_hidden(h_field2))

        with self.assertNumQueries(0):
            lc.get_4_model(model1)
