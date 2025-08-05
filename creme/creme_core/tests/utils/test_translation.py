from unittest import skipIf

from django.conf import settings
from django.utils.translation import gettext as _
from django.utils.translation import override as override_language

from creme.creme_core.models import (
    CustomEntityType,
    FakeContact,
    FakeOrganisation,
)
# from creme.creme_core.utils.translation import get_model_verbose_name
from creme.creme_core.utils.translation import (
    plural,
    smart_model_verbose_name,
    verbose_instances_groups,
)

from ..base import CremeTestCase


class TranslationTestCase(CremeTestCase):
    def _enable_custom_type(self, id, name, plural_name):
        ce_type = self.get_object_or_fail(CustomEntityType, id=id)
        ce_type.enabled = True
        ce_type.name = name
        ce_type.plural_name = plural_name
        ce_type.save()

        return ce_type

    @skipIf(settings.USE_I18N, "This test is made for <USE_I18N==False>")
    def test_plural__no_i18n(self):
        self.assertTrue(plural(0))
        self.assertFalse(plural(1))
        self.assertTrue(plural(2))

    @skipIf(not settings.USE_I18N, "This test is made for <USE_I18N==True>")
    def test_plural__i18n(self):
        with override_language('en'):
            self.assertTrue(plural(0))
            self.assertFalse(plural(1))
            self.assertTrue(plural(2))

        with override_language('fr'):
            self.assertFalse(plural(0))
            self.assertFalse(plural(1))
            self.assertTrue(plural(2))

    # @skipIf(not settings.USE_I18N, "This test is made for <USE_I18N==False>")
    # def test_get_model_verbose_name__i18n(self):  # DEPRECATED
    #     ce_type1 = self._enable_custom_type(id=1, name='Shop',    plural_name='Shops')
    #     ce_type2 = self._enable_custom_type(id=2, name='Country', plural_name='Countries')
    #
    #     with override_language('en'):
    #         self.assertEqual('Test Contacts', get_model_verbose_name(FakeContact, 0))
    #         self.assertEqual('Test Contact',  get_model_verbose_name(FakeContact, 1))
    #         self.assertEqual('Test Contacts', get_model_verbose_name(FakeContact, count=2))
    #
    #         self.assertEqual('Test Organisation', get_model_verbose_name(FakeOrganisation, 1))
    #
    #         self.assertEqual(
    #             ce_type1.name, get_model_verbose_name(ce_type1.entity_model, count=1),
    #         )
    #         self.assertEqual(
    #             ce_type2.name, get_model_verbose_name(ce_type2.entity_model, count=1),
    #         )
    #         self.assertEqual(
    #             ce_type1.plural_name, get_model_verbose_name(ce_type1.entity_model, count=2),
    #         )
    #
    #     with override_language('fr'):
    #         self.assertEqual('Test Contact',  get_model_verbose_name(FakeContact, 0))
    #         self.assertEqual('Test Contact',  get_model_verbose_name(FakeContact, 1))
    #         self.assertEqual('Test Contacts', get_model_verbose_name(FakeContact, count=2))

    @skipIf(settings.USE_I18N, "This test is made for <USE_I18N==False>")
    def test_smart_model_verbose_name__no_i18n(self):
        self.assertEqual('Test Contact', smart_model_verbose_name(FakeContact, 1))
        self.assertEqual('Test Contacts', smart_model_verbose_name(FakeContact, count=2))

        self.assertEqual('Test Organisation', smart_model_verbose_name(FakeOrganisation, 1))

    @skipIf(not settings.USE_I18N, "This test is made for <USE_I18N==True>")
    def test_smart_model_verbose_name__i18n(self):
        ce_type1 = self._enable_custom_type(id=1, name='Shop',    plural_name='Shops')
        ce_type2 = self._enable_custom_type(id=2, name='Country', plural_name='Countries')

        with override_language('en'):
            self.assertEqual('Test Contacts', smart_model_verbose_name(FakeContact, 0))
            self.assertEqual('Test Contact', smart_model_verbose_name(FakeContact, 1))
            self.assertEqual('Test Contacts', smart_model_verbose_name(FakeContact, count=2))

            self.assertEqual('Test Organisation', smart_model_verbose_name(FakeOrganisation, 1))

            self.assertEqual(
                ce_type1.name, smart_model_verbose_name(ce_type1.entity_model, count=1),
            )
            self.assertEqual(
                ce_type2.name, smart_model_verbose_name(ce_type2.entity_model, count=1),
            )
            self.assertEqual(
                ce_type1.plural_name, smart_model_verbose_name(ce_type1.entity_model, count=2),
            )

        with override_language('fr'):
            self.assertEqual('Test Contact', smart_model_verbose_name(FakeContact, 0))
            self.assertEqual('Test Contact', smart_model_verbose_name(FakeContact, 1))
            self.assertEqual('Test Contacts', smart_model_verbose_name(FakeContact, count=2))

    @skipIf(settings.USE_I18N, "This test is made for <USE_I18N==False>")
    def test_verbose_instances_groups__no_i18n(self):
        fmt = _('{count} {model}').format

        self.assertCountEqual(
            [
                fmt(count=2, model='Test Contacts'),
                fmt(count=1, model='Test Organisation'),
            ],
            [
                *verbose_instances_groups(instances=[
                    FakeContact(), FakeOrganisation(), FakeContact(),
                ]),
            ],
        )

    @skipIf(not settings.USE_I18N, "This test is made for <USE_I18N==True>")
    def test_verbose_instances_groups__i18n(self):
        with override_language('fr'):
            fmt = _('{count} {model}').format

            self.assertCountEqual(
                [
                    fmt(count=2, model='Test Contacts'),
                    fmt(count=1, model='Test Organisation'),
                ],
                [
                    *verbose_instances_groups(instances=[
                        FakeContact(), FakeOrganisation(), FakeContact(),
                    ]),
                ],
            )

        # TODO: test with a language with a rule for plural different from en/fr
