from django.urls import reverse
from django.utils.translation import gettext as _

from creme.billing.actions import (
    ExportInvoiceAction,
    ExportQuoteAction,
    GenerateCreditNoteNumberAction,
    GenerateInvoiceNumberAction,
)
from creme.creme_core.gui import actions

from .base import _BillingTestCase


class ListviewActionsTestCase(_BillingTestCase):
    def test_export__quote(self):
        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='Quote #1')[0]

        export_action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=quote)
            if isinstance(action, ExportQuoteAction)
        )
        self.assertEqual('billing-export_quote', export_action.id)
        self.assertEqual('redirect', export_action.type)
        self.assertEqual(reverse('billing__export', args=(quote.id,)), export_action.url)
        self.assertTrue(export_action.is_enabled)
        self.assertTrue(export_action.is_visible)

    def test_export__invoice(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice #1')[0]

        export_action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=invoice)
            if isinstance(action, ExportInvoiceAction)
        )
        self.assertEqual('billing-export_invoice', export_action.id)
        self.assertEqual('redirect', export_action.type)
        self.assertEqual(
            reverse('billing__export', args=(invoice.id,)),
            export_action.url,
        )
        self.assertTrue(export_action.is_enabled)
        self.assertTrue(export_action.is_visible)

    def test_generate_number__invoice(self):
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user)
        self._set_managed(source)

        invoice = self.create_invoice(
            user=user, name='Invoice 0001', source=source, target=target,
        )

        action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=invoice)
            if isinstance(action, GenerateInvoiceNumberAction)
        )
        self.assertEqual('billing-invoice_number', action.id)
        self.assertEqual('billing-number', action.type)
        self.assertEqual(
            reverse('billing__generate_number', args=(invoice.id,)),
            action.url,
        )
        self.assertTrue(action.is_enabled)
        self.assertTrue(action.is_visible)
        self.assertEqual('', action.help_text)
        self.assertDictEqual(
            {
                'data': {},
                'options': {
                    'confirm': _('Do you really want to generate a number?'),
                },
            },
            action.action_data,
        )

    def test_generate_number__invoice__no_config(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice #1')[0]

        action = GenerateInvoiceNumberAction(user=user, instance=invoice)
        self.assertFalse(action.is_enabled)
        self.assertTrue(action.is_visible)
        self.assertEqual(
            _('This entity cannot generate a number (see configuration of the app Billing)'),
            action.help_text,
        )

    def test_generate_number__invoice__number_already_fill(self):
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user)
        self._set_managed(source)

        invoice = self.create_invoice(
            user=user, name='Invoice 0001', source=source, target=target,
            number='J03',
        )

        action = GenerateInvoiceNumberAction(user=user, instance=invoice)
        self.assertFalse(action.is_enabled)
        self.assertTrue(action.is_visible)
        self.assertEqual(_('This entity has already a number'), action.help_text)

    def test_generate_number__credit_note(self):
        user = self.login_as_root_and_get()
        cnote = self.create_credit_note_n_orgas(user=user, name='Quotee 0001')[0]

        action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=cnote)
            if isinstance(action, GenerateCreditNoteNumberAction)
        )
        self.assertEqual('billing-creditnote_number', action.id)
        self.assertEqual('billing-number', action.type)
        self.assertEqual(
            reverse('billing__generate_number', args=(cnote.id,)),
            action.url,
        )
