from unittest import skipIf

from django.conf import settings
from django.utils.translation import override as override_language

from creme.creme_core.utils.translation import get_model_verbose_name, plural

from ..base import CremeTestCase
from ..fake_models import FakeContact, FakeOrganisation


class TranslationTestCase(CremeTestCase):
    @skipIf(settings.USE_I18N, "This test is made for <USE_I18N==True>")
    def test_plural__no_i18n(self):
        self.assertTrue(plural(0))
        self.assertFalse(plural(1))
        self.assertTrue(plural(2))

    @skipIf(not settings.USE_I18N, "This test is made for <USE_I18N==False>")
    def test_plural__i18n(self):
        with override_language('en'):
            self.assertTrue(plural(0))
            self.assertFalse(plural(1))
            self.assertTrue(plural(2))

        with override_language('fr'):
            self.assertFalse(plural(0))
            self.assertFalse(plural(1))
            self.assertTrue(plural(2))

    @skipIf(settings.USE_I18N, "This test is made for <USE_I18N==True>")
    def test_get_model_verbose_name__no_i18n(self):
        self.assertEqual('Test Contact',  get_model_verbose_name(FakeContact, 1))
        self.assertEqual('Test Contacts', get_model_verbose_name(FakeContact, count=2))

        self.assertEqual('Test Organisation',  get_model_verbose_name(FakeOrganisation, 1))

    @skipIf(not settings.USE_I18N, "This test is made for <USE_I18N==False>")
    def test_get_model_verbose_name__i18n(self):
        with override_language('en'):
            self.assertEqual('Test Contacts', get_model_verbose_name(FakeContact, 0))
            self.assertEqual('Test Contact',  get_model_verbose_name(FakeContact, 1))
            self.assertEqual('Test Contacts', get_model_verbose_name(FakeContact, count=2))

            self.assertEqual('Test Organisation', get_model_verbose_name(FakeOrganisation, 1))

        with override_language('fr'):
            self.assertEqual('Test Contact',  get_model_verbose_name(FakeContact, 0))
            self.assertEqual('Test Contact',  get_model_verbose_name(FakeContact, 1))
            self.assertEqual('Test Contacts', get_model_verbose_name(FakeContact, count=2))
