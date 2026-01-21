from django.urls import reverse

from creme.creme_core.gui import actions
from creme.emails.actions import (
    BulkEntityEmailResendAction,
    EntityEmailResendAction,
)

from .base import EntityEmail, _EmailsTestCase


class EmailsActionsTestCase(_EmailsTestCase):
    def test_instance_actions(self):
        user = self.login_as_root_and_get()
        email = self._create_email(user=user)

        resend_action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=email)
            if isinstance(action, EntityEmailResendAction)
        )
        self.assertEqual('email-resend', resend_action.type)
        self.assertEqual(reverse('emails__resend_emails'), resend_action.url)
        self.assertDictEqual(
            {
                'data': {},
                'options': {'selection': [email.id]},
            },
            resend_action.action_data,
        )
        self.assertTrue(resend_action.is_enabled)
        self.assertTrue(resend_action.is_visible)

    def test_bulk_actions(self):
        user = self.login_as_root_and_get()
        resend_action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .bulk_actions(user=user, model=EntityEmail)
            if isinstance(action, BulkEntityEmailResendAction)
        )
        self.assertEqual('email-resend-selection', resend_action.type)
        self.assertEqual(reverse('emails__resend_emails'), resend_action.url)
        self.assertIsNone(resend_action.action_data)
        self.assertTrue(resend_action.is_enabled)
        self.assertTrue(resend_action.is_visible)
