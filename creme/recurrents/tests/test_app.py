from django.contrib.contenttypes.models import ContentType

from creme.creme_core.forms import CremeEntityForm
from creme.creme_core.models import HeaderFilter
from creme.creme_core.tests.base import CremeTestCase

from ..models import FakeRecurrentDoc, FakeRecurrentTemplate
from ..registry import RecurrentRegistry
from .base import RecurrentGenerator


class RecurrentsAppTestCase(CremeTestCase):
    def test_populate(self):
        self.assertTrue(HeaderFilter.objects.filter(
            entity_type=ContentType.objects.get_for_model(RecurrentGenerator)
        ))

    def test_registry(self):
        user = self.get_root_user()

        registry = RecurrentRegistry()
        self.assertFalse([*registry.models])
        self.assertIsNone(
            registry.get_template_form_class(model=FakeRecurrentDoc, user=user)
        )

        class FakeRecurrentTemplateForm(CremeEntityForm):
            class Meta(CremeEntityForm.Meta):
                model = FakeRecurrentTemplate

        registry.register(
            (FakeRecurrentDoc, FakeRecurrentTemplate, FakeRecurrentTemplateForm),
        )
        self.assertListEqual([FakeRecurrentDoc], [*registry.models])
        self.assertEqual(
            FakeRecurrentTemplateForm,
            registry.get_template_form_class(model=FakeRecurrentDoc, user=user),
        )

    # TODO: test with CustomForm
    # TODO: add views tests with fake models
