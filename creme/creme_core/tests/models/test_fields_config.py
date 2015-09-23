# -*- coding: utf-8 -*-

try:
    from json import loads as jsonloads, dumps as jsondumps

    from django.contrib.contenttypes.models import ContentType

    from ..base import CremeTestCase
    from ..fake_forms import FakeContactForm
    from ..fake_models import FakeContact

    from creme.creme_core.models import FieldsConfig
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class FieldsConfigTestCase(CremeTestCase):
    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        cls.populate('creme_core')

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

        #last_name = u'Senjōgahara' MySQL does not like this....
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

        with self.assertNoException(): # KeyError...
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
                    raw_descriptions=jsondumps([(h_field,   {FieldsConfig.HIDDEN: True}),
                                                ('invalid', {FieldsConfig.HIDDEN: True}),
                                               ]
                                              ),
                 )

        fconf = self.refresh(fconf)
        self.assertEqual(1, len(fconf.descriptions))

        fconf = self.refresh(fconf)
        self.assertEqual(1, len(jsonloads(fconf.raw_descriptions)))
        self.assertTrue(fconf.is_field_hidden(FakeContact._meta.get_field(h_field)))

    def test_ct_cache(self):
        model = FakeContact
        ContentType.objects.get_for_model(model) # ensure that ContentType is filled

        fconf = FieldsConfig.create(model,
                                    descriptions=[('last_name', {FieldsConfig.HIDDEN: True})],
                                   )
        fconf = self.refresh(fconf)

        with self.assertNumQueries(0):
            ct = fconf.content_type

        self.assertEqual(FakeContact, ct.model_class())
