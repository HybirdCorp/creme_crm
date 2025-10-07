from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from creme.creme_core.core.exceptions import ConflictError
from creme.creme_core.models import SettingValue
from creme.persons.tests.base import (
    skipIfCustomContact,
    skipIfCustomOrganisation,
)

from .. import buttons
from ..constants import REL_OBJ_BILL_RECEIVED
from ..core import conversion
from ..setting_keys import button_redirection_key
from .base import (
    Contact,
    Invoice,
    Organisation,
    Quote,
    SalesOrder,
    _BillingTestCase,
)


class ButtonsTestCase(_BillingTestCase):
    def test_generate_number__emitter_not_managed(self):
        button = buttons.GenerateNumberButton()

        user = self.get_root_user()
        request = self.build_request(user=user)

        # ---
        emitter, receiver = self.create_orgas(user=user)
        invoice = Invoice.objects.create(
            user=user, name='Invoice001', source=emitter, target=receiver,
        )
        # self.assertTrue(button.ok_4_display(invoice))
        self.assertTrue(button.is_displayed(entity=invoice, request=request))

        ctxt1 = button.get_context(entity=invoice, request=request)
        self.assertEqual(
            _('This entity cannot generate a number (see configuration of the app Billing)'),
            ctxt1.get('permission_error'),
        )

        # ---
        quote = Quote(user=user)
        # self.assertFalse(button.ok_4_display(quote))
        self.assertFalse(button.is_displayed(entity=quote, request=request))

    def test_generate_number__emitter_is_managed(self):
        button = buttons.GenerateNumberButton()

        user = self.get_root_user()
        request = self.build_request(user=user)

        # ---
        emitter, receiver = self.create_orgas(user=user)
        self._set_managed(emitter)
        invoice = Invoice.objects.create(
            user=user, name='Invoice001', source=emitter, target=receiver,
        )

        ctxt1 = button.get_context(entity=invoice, request=request)
        self.assertNotIn('permission_error', ctxt1)

        # ---
        invoice.number = 'IN-123'

        ctxt2 = button.get_context(entity=invoice, request=request)
        with self.assertNoException():
            error2 = ctxt2['permission_error']
        self.assertEqual(_('This entity has already a number'), error2)

    @skipIfCustomOrganisation
    def test_add_invoice(self):
        button = buttons.AddInvoiceButton()

        # ---
        user1 = self.create_user(
            index=0,
            role=self.create_role(
                name='Invoice master', allowed_apps=['persons', 'billing'],
                creatable_models=[Invoice],
            ),
        )
        self.add_credentials(user1.role, all=['LINK'])
        request1 = self.build_request(user=user1)

        orga = Organisation.objects.create(user=self.get_root_user(), name='Acme')
        # self.assertTrue(button.ok_4_display(orga))
        self.assertTrue(button.is_displayed(entity=orga, request=request1))

        ctxt = button.get_context(entity=orga, request=request1)
        self.assertEqual('billing__create_related_invoice', ctxt.get('url_name'))
        self.assertEqual(_('Invoice'),                      ctxt.get('model_vname'))
        self.assertEqual('billing.invoice',                 ctxt.get('model_id'))
        self.assertEqual(REL_OBJ_BILL_RECEIVED,             ctxt.get('rtype_id'))
        self.assertTrue(ctxt.get('redirect'))
        self.assertIsNone(ctxt.get('permission_error'))

        # ---
        user2 = self.create_user(
            index=1,
            role=self.create_role(
                name='Quote master', allowed_apps=['billing'], creatable_models=[Quote],
            ),
        )
        self.add_credentials(user1.role, all=['LINK', 'VIEW'])

        with self.assertRaises(PermissionDenied) as cm:
            button.check_permissions(entity=orga, request=self.build_request(user=user2))
        self.assertEqual(
            _('You are not allowed to create: {}').format(_('Invoice')),
            str(cm.exception),
        )

    @skipIfCustomContact
    def test_add_quote(self):
        button = buttons.AddQuoteButton()

        SettingValue.objects.set_4_key(button_redirection_key, False)

        # ---
        user1 = self.create_user(
            index=0,
            role=self.create_role(
                name='Quote master', allowed_apps=['persons', 'billing'],
                creatable_models=[Quote],
            ),
        )
        self.add_credentials(user1.role, all=['LINK'])

        request1 = self.build_request(user=user1)

        contact = Contact.objects.create(
            user=self.get_root_user(), first_name='John', last_name='Doe',
        )

        ctxt = button.get_context(entity=contact, request=request1)
        self.assertEqual('billing__create_related_quote', ctxt.get('url_name'))
        self.assertEqual(_('Quote'),                      ctxt.get('model_vname'))
        self.assertEqual('billing.quote',                 ctxt.get('model_id'))
        self.assertFalse(ctxt.get('redirect'))
        self.assertIsNone(ctxt.get('permission_error'))

        # ---
        user2 = self.create_user(
            index=1,
            role=self.create_role(
                name='Invoice master', allowed_apps=['billing'], creatable_models=[Invoice],
            ),
        )

        with self.assertRaises(PermissionDenied) as cm:
            button.check_permissions(entity=contact, request=self.build_request(user=user2))
        self.assertEqual(
            _('You are not allowed to create: {}').format(_('Quote')),
            str(cm.exception),
        )

    @skipIfCustomOrganisation
    def test_add_sales_order(self):
        button = buttons.AddSalesOrderButton()

        user = self.get_root_user()
        request = self.build_request(user=user)

        orga = Organisation.objects.create(user=user, name='Acme')
        ctxt = button.get_context(entity=orga, request=request)
        self.assertEqual('billing__create_related_order', ctxt.get('url_name'))
        self.assertEqual('billing.salesorder',            ctxt.get('model_id'))

    def test_convert_to_invoice(self):
        button = buttons.ConvertToInvoiceButton()
        self.assertCountEqual([Quote, SalesOrder], button.get_ctypes())

        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]

        request = self.build_request(user=user)

        ctxt1 = button.get_context(entity=quote, request=request)
        self.assertEqual('invoice',    ctxt1.get('convert_to'))
        self.assertEqual(_('Invoice'), ctxt1.get('model_vname'))
        self.assertNotIn('permission_error', ctxt1)

        # No converter ---
        button.converter_registry = registry = conversion.ConverterRegistry()
        ctxt2 = button.get_context(entity=quote, request=request)
        self.assertEqual(
            _('This conversion has been removed; you should remove this button.'),
            ctxt2.get('permission_error'),
        )

        # Forbidden ---
        error_msg = 'Nope'

        class ForbiddenConverter(conversion.Converter):
            def check_permissions(this):
                raise ConflictError(error_msg)

        registry.register(
            source_model=Quote, target_model=Invoice, converter_class=ForbiddenConverter,
        )
        ctxt3 = button.get_context(entity=quote, request=request)
        self.assertEqual(error_msg, ctxt3.get('permission_error'))

    def test_convert_to_salesorder(self):
        button = buttons.ConvertToSalesOrderButton()
        self.assertListEqual([Quote], [*button.get_ctypes()])

        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]

        request = self.build_request(user=user)

        ctxt = button.get_context(entity=quote, request=request)
        self.assertEqual('sales_order', ctxt.get('convert_to'))
        self.assertEqual(_('Salesorder'), ctxt.get('model_vname'))
        self.assertNotIn('permission_error', ctxt)

    def test_convert_to_quote(self):
        button = buttons.ConvertToQuoteButton()
        self.assertListEqual([Invoice], [*button.get_ctypes()])

        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='My Quote')[0]

        request = self.build_request(user=user)

        ctxt = button.get_context(entity=invoice, request=request)
        self.assertEqual('quote', ctxt.get('convert_to'))
        self.assertEqual(_('Quote'), ctxt.get('model_vname'))
        self.assertNotIn('permission_error', ctxt)
