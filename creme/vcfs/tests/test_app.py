# -*- coding: utf-8 -*-

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.gui.actions import actions_registry
from creme.creme_core.tests.base import CremeTestCase
from creme.vcfs.actions import GenerateVcfAction


class VcfsTestCase(CremeTestCase):
    def test_config(self):
        "Should not be available when creating UserRoles."
        self.login()

        response = self.assertGET200(reverse('creme_config__create_role'))

        with self.assertNoException():
            app_labels = response.context['form'].fields['allowed_apps'].choices

        self.assertInChoices(
            value='creme_core', label=_('Core'), choices=app_labels
        )
        self.assertInChoices(
            value='persons', label=_('Accounts and Contacts'), choices=app_labels
        )
        self.assertNotInChoices(value='vcfs', choices=app_labels)  # <==

    def test_actions(self):
        user = self.login()
        contact = user.linked_contact
        vcfs_actions = [
            action
            for action in actions_registry.instance_actions(user=user, instance=contact)
            if isinstance(action, GenerateVcfAction)
        ]
        self.assertEqual(1, len(vcfs_actions))

        action = vcfs_actions[0]
        self.assertEqual('redirect', action.type)
        self.assertEqual(reverse('vcfs__export', args=(contact.id,)), action.url)
        self.assertTrue(action.is_enabled)  # TODO: test with credentials
        self.assertTrue(action.is_visible)
