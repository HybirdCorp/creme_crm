# -*- coding: utf-8 -*-

try:
    from json import loads as jsonloads

    from django.contrib.contenttypes.models import ContentType

    from creme.creme_core.tests.base import CremeTestCase
    from creme.creme_core.tests.fake_models import (FakeContact, FakeAddress,
            FakeCivility, FakeEmailCampaign)
    from creme.creme_core.forms.widgets import Label
    from creme.creme_core.gui.fields_config import fields_config_registry
    from creme.creme_core.models import FieldsConfig
    from creme.creme_core.registry import creme_registry
except Exception as e:
    print('Error in <%s>: %s' % (__name__, e))


class FieldsConfigTestCase(CremeTestCase):
    ADD_CTYPE_URL = '/creme_config/fields/add/'

    @classmethod
    def setUpClass(cls):
        CremeTestCase.setUpClass()
        # cls.populate('creme_core')

        cls.ct = ContentType.objects.get_for_model(FakeContact)

        # TODO: unregister in tearDownClass ?? move to fake app.ready() ?
        fields_config_registry.register(FakeAddress)

    def setUp(self):
        self.login()

    def _build_edit_url(self, fconf):
        return '/creme_config/fields/edit/%s' % fconf.pk

    def _create_fconf(self):
        ct = self.ct
        self.assertNoFormError(self.client.post(self.ADD_CTYPE_URL, data={'ctype': ct.id}))
        return self.get_object_or_fail(FieldsConfig, content_type=ct)

    def test_portal(self):
        response = self.assertGET200('/creme_config/fields/portal/')
        self.assertTemplateUsed(response, 'creme_config/fields_config_portal.html')

    def test_add01(self):
        ct = self.ct
        self.assertFalse(FieldsConfig.objects.filter(content_type=ct))

        url = self.ADD_CTYPE_URL
        response = self.assertGET200(url)

        with self.assertNoException():
            ctypes = response.context['form'].fields['ctype'].ctypes

        self.assertIn(ct, ctypes)

        self.assertIn(FakeEmailCampaign, creme_registry.iter_entity_models())
        self.assertNotIn(ContentType.objects.get_for_model(FakeEmailCampaign), ctypes)

        fconf = self._create_fconf()
        self.assertEqual([], jsonloads(fconf.raw_descriptions)) #TODO: bof bof

        # ---------------
        response = self.assertGET200(url)

        with self.assertNoException():
            ctypes = response.context['form'].fields['ctype'].ctypes

        self.assertNotIn(ct, ctypes)

    def test_add02(self):
        "Not a CremeEntity : must be registered"
        get_ct = ContentType.objects.get_for_model
        ct_addr = get_ct(FakeAddress)
        ct_civ  = get_ct(FakeCivility)
        self.assertFalse(FieldsConfig.objects.filter(content_type=ct_addr))

        url = self.ADD_CTYPE_URL
        response = self.assertGET200(url)

        with self.assertNoException():
            ctypes = response.context['form'].fields['ctype'].ctypes

        self.assertNotIn(ct_civ, ctypes)
        self.assertIn(ct_addr, ctypes)

    def test_add03(self):
        "All CTypes are already configured"
        used_ct_ids = set(FieldsConfig.objects.values_list('content_type', flat=True))
        FieldsConfig.objects.bulk_create([FieldsConfig(content_type=ct)
                                            for ct in fields_config_registry.ctypes
                                                if ct.id not in used_ct_ids
                                         ]
                                        )

        response = self.assertGET200(self.ADD_CTYPE_URL)

        with self.assertNoException():
            ctype_f = response.context['form'].fields['ctype']

        self.assertIsInstance(ctype_f.widget, Label)

    def test_edit(self):
        get_field = FakeContact._meta.get_field
        self.assertTrue(get_field('phone').get_tag('optional'))
        self.assertTrue(get_field('birthday').get_tag('optional'))
        self.assertFalse(get_field('last_name').get_tag('optional'))
        self.assertTrue(get_field('image').get_tag('optional'))

        # --------
        fconf = self._create_fconf()

        url = self._build_edit_url(fconf)
        response = self.assertGET200(url)

        with self.assertNoException():
            choices = response.context['form'].fields['hidden'].choices
            choices_keys = {k for k, v in choices}

        self.assertIn('phone',    choices_keys)
        self.assertIn('birthday', choices_keys)
        self.assertNotIn('last_name', choices_keys)
        self.assertIn('image', choices_keys)
        self.assertNotIn('image__description', choices_keys)

        response = self.client.post(url, data={'hidden': ['phone', 'birthday']})
        self.assertNoFormError(response)

        fconf = self.refresh(fconf)
        self.assertEqual([['phone', {'hidden': True}], ['birthday', {'hidden': True}]],
                         jsonloads(fconf.raw_descriptions)
                        ) #TODO: bof bof

        # test initial ------
        response = self.assertGET200(url)

        with self.assertNoException():
            hidden_f = response.context['form'].fields['hidden']

        self.assertEqual(['phone', 'birthday'], hidden_f.initial)

    def test_delete(self):
        fconf = self._create_fconf()

        self.assertPOST200('/creme_config/fields/delete', data={'id': fconf.pk})
        self.assertDoesNotExist(fconf)
