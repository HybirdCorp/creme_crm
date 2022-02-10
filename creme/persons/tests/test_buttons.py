# -*- coding: utf-8 -*-

from parameterized import parameterized

from creme.creme_core.models import Relation
from creme.creme_core.tests.base import CremeTestCase
from creme.persons import buttons

from .base import Organisation, skipIfCustomOrganisation


@skipIfCustomOrganisation
class ButtonsTestCase(CremeTestCase):
    @parameterized.expand([
        (buttons.BecomeCustomerButton, ),
        (buttons.BecomeProspectButton, ),
        (buttons.BecomeSuspectButton, ),
        (buttons.BecomeInactiveButton, ),
        (buttons.BecomeSupplierButton, ),
    ])
    def test_become(self, button_class):
        user = self.create_user()

        managed_orgas = [*Organisation.objects.filter_managed_by_creme().all()]
        self.assertEqual(1, len(managed_orgas))

        managed_orga = managed_orgas[0]
        orga = Organisation.objects.create(user=user, name='Acme')

        button = button_class()
        self.assertTrue(button.ok_4_display(orga))

        # Already linked
        Relation.objects.create(
            user=user,
            subject_entity=orga,
            type_id=button.relation_type_id,
            object_entity=managed_orga,
        )
        self.assertFalse(button.ok_4_display(orga))

    def test_become_error(self):
        "Cannot link a managed organisation with itself."
        self.create_user()

        managed_orgas = [*Organisation.objects.filter_managed_by_creme().all()]
        self.assertEqual(1, len(managed_orgas))

        managed_orga = managed_orgas[0]

        button = buttons.BecomeCustomerButton()
        self.assertFalse(button.ok_4_display(managed_orga))
