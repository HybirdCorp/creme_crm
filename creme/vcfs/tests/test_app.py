from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.gui.actions import action_registry
from creme.creme_core.tests.base import CremeTestCase
from creme.vcfs.actions import GenerateVcfAction


class VcfsTestCase(CremeTestCase):
    def test_config(self):
        "Should not be available when creating UserRoles."
        self.login_as_root()

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
        user = self.login_as_root_and_get()
        contact = user.linked_contact
        action = self.get_alone_element(
            action
            for action in action_registry.instance_actions(user=user, instance=contact)
            if isinstance(action, GenerateVcfAction)
        )
        self.assertEqual('redirect', action.type)
        self.assertEqual(reverse('vcfs__export', args=(contact.id,)), action.url)
        self.assertTrue(action.is_enabled)  # TODO: test with credentials
        self.assertTrue(action.is_visible)
