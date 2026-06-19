from creme.creme_core.models import CremeProperty, FakeContact, Relation
from creme.creme_core.tests.base import CremeTestCase
from creme.creme_core.utils.model import safe_model, update_model_instance


class ModelTestCase(CremeTestCase):
    def test_safe_model(self):
        self.assertEqual(CremeProperty, safe_model(CremeProperty))
        self.assertEqual(Relation,      safe_model(Relation))

        self.assertEqual(CremeProperty, safe_model('creme_core.CremeProperty'))
        self.assertEqual(Relation,      safe_model('creme_core.Relation'))

    def test_update_model_instance(self):
        user = self.get_root_user()
        first_name = 'punpun'
        last_name = 'punpunyama'
        contact = FakeContact.objects.create(
            user=user, first_name=first_name, last_name=last_name,
        )

        first_name = first_name.title()

        update_model_instance(contact, first_name=first_name)
        self.assertEqual(first_name, self.refresh(contact).first_name)

        with self.assertNumQueries(0):
            update_model_instance(contact, last_name=last_name)

        self.assertRaises(
            AttributeError,
            update_model_instance,
            contact, first_name=first_name, unknown_field='??',
        )

    def test_update_model_instance__several_fields(self):
        first_name = 'punpun'
        last_name = 'punpunyama'
        contact = FakeContact.objects.create(
            user=self.get_root_user(), first_name=first_name, last_name=last_name,
        )

        first_name = first_name.title()
        last_name = last_name.title()
        update_model_instance(contact, first_name=first_name, last_name=last_name)

        contact = self.refresh(contact)
        self.assertEqual(first_name, contact.first_name)
        self.assertEqual(last_name,  contact.last_name)

        with self.assertNumQueries(0):
            update_model_instance(contact, first_name=first_name, last_name=last_name)
