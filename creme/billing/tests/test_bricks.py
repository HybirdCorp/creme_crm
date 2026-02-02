from datetime import date
from functools import partial

from django.test.utils import override_settings
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext as _

from creme.billing import bricks as billing_bricks
from creme.billing.models import (
    CreditNoteStatus,
    InvoiceStatus,
    NumberGeneratorItem,
    PaymentInformation,
    QuoteStatus,
    SalesOrderStatus,
)
from creme.billing.setting_keys import payment_info_key
from creme.creme_core.models import (
    BrickDetailviewLocation,
    FieldsConfig,
    SettingValue,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

from .base import (
    Address,
    CreditNote,
    Invoice,
    Organisation,
    Quote,
    SalesOrder,
    _BillingTestCase,
    skipIfCustomCreditNote,
    skipIfCustomInvoice,
    skipIfCustomQuote,
)


@skipIfCustomOrganisation
class ConfigurationBricksTestCase(BrickTestCaseMixin, _BillingTestCase):
    def test_NumberGeneratorItemsBrick(self):
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='Acme')
        NumberGeneratorItem.objects.create(
            organisation=orga, numbered_type=Invoice,
            data={'format': 'INV{counter:04}', 'reset': 'never'},
        )

        response = self.assertGET200(
            reverse('creme_config__app_portal', args=('billing',))
        )
        brick_node = self.get_brick_node(
            tree=self.get_html_tree(response.content),
            brick=billing_bricks.NumberGeneratorItemsBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Organisation configured for number generation',
            plural_title='{count} Organisations configured for number generation',
        )
        self.assertInstanceLink(brick_node, entity=orga)
        # TODO: complete


@skipIfCustomOrganisation
class ReceivedBillingEntitiesBricksTestCase(BrickTestCaseMixin, _BillingTestCase):
    @skipIfCustomCreditNote
    def test_ReceivedCreditNotesBrick(self):
        user = self.login_as_root_and_get()
        BrickDetailviewLocation.objects.create_if_needed(
            brick=billing_bricks.ReceivedCreditNotesBrick, order=600,
            zone=BrickDetailviewLocation.RIGHT, model=Organisation,
        )

        source, target = self.create_orgas(user=user)

        response1 = self.assertGET200(target.get_absolute_url())
        brick_node1 = self.get_brick_node(
            self.get_html_tree(response1.content),
            brick=billing_bricks.ReceivedCreditNotesBrick,
        )
        self.assertEqual(_('Received credit notes'), self.get_brick_title(brick_node1))

        # ---
        credit_note = CreditNote.objects.create(
            user=user, name='My Quote',
            status=CreditNoteStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
        )

        response2 = self.assertGET200(target.get_absolute_url())
        brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content),
            brick=billing_bricks.ReceivedCreditNotesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node2,
            count=1,
            title='{count} Received credit note',
            plural_title='{count} Received credit notes',
        )
        self.assertListEqual(
            [_('Name'), _('Expiration date'), _('Status'), _('Total without VAT'), _('Action')],
            self.get_brick_table_column_titles(brick_node2),
        )
        rows = self.get_brick_table_rows(brick_node2)
        table_cells = self.get_alone_element(rows).findall('.//td')
        self.assertEqual(5, len(table_cells))
        self.assertInstanceLink(table_cells[0], entity=credit_note)

    def test_ReceivedInvoicesBrick(self):
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user=user)

        response1 = self.assertGET200(target.get_absolute_url())
        brick_node1 = self.get_brick_node(
            self.get_html_tree(response1.content),
            brick=billing_bricks.ReceivedInvoicesBrick,
        )
        self.assertEqual(_('Received invoices'), self.get_brick_title(brick_node1))

        # ---
        invoice = Invoice.objects.create(
            user=user, name='My Invoice',
            status=InvoiceStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
            number='INV123',
        )

        # ----
        response2 = self.assertGET200(target.get_absolute_url())
        brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content),
            brick=billing_bricks.ReceivedInvoicesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node2,
            count=1,
            title='{count} Received invoice',
            plural_title='{count} Received invoices',
        )
        self.assertListEqual(
            [
                _('Name'), _('Number'), _('Expiration date'), _('Status'),
                _('Total without VAT'), _('Action'),
            ],
            self.get_brick_table_column_titles(brick_node2),
        )
        rows = self.get_brick_table_rows(brick_node2)
        table_cells = self.get_alone_element(rows).findall('.//td')
        self.assertEqual(6, len(table_cells))
        self.assertInstanceLink(table_cells[0], entity=invoice)
        self.assertEqual(invoice.number, table_cells[1].text)
        self.assertEqual(
            date_format(invoice.expiration_date, 'DATE_FORMAT'),
            table_cells[2].text,
        )
        self.assertEqual(invoice.status.name, table_cells[3].text)
        # TODO: test table_cells[4]

        # ----
        context = self.build_context(user=user, instance=target)
        # Queries:
        #   - FieldsConfig
        #   - COUNT Invoices
        #   - BrickStates
        #   - SettingValues "is open"/"how empty fields"
        #   - Invoices
        #   - SettingValues "creme_core-display_currency_local_symbol"
        with self.assertNumQueries(6):
            render = billing_bricks.ReceivedInvoicesBrick().detailview_display(context)

        brick_node3 = self.get_brick_node(
            self.get_html_tree(render), brick=billing_bricks.ReceivedInvoicesBrick,
        )
        self.assertInstanceLink(brick_node3, entity=invoice)

    def test_ReceivedInvoicesBrick__hidden_expiration(self):
        "Field 'expiration_date' is hidden."
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user=user)

        FieldsConfig.objects.create(
            content_type=Invoice,
            descriptions=[
                ('expiration_date',  {FieldsConfig.HIDDEN: True}),
            ],
        )

        Invoice.objects.create(
            user=user, name='My Quote',
            status=InvoiceStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
        )

        response = self.assertGET200(target.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.ReceivedInvoicesBrick,
        )
        self.assertListEqual(
            [_('Name'), _('Number'), _('Status'), _('Total without VAT'), _('Action')],
            self.get_brick_table_column_titles(brick_node),
        )
        rows = self.get_brick_table_rows(brick_node)
        row = self.get_alone_element(rows)
        self.assertEqual(5, len(row.findall('.//td')))

    @override_settings(HIDDEN_VALUE='?')
    def test_ReceivedInvoicesBrick__forbidden(self):
        "No VIEW permission."
        user = self.login_as_standard(allowed_apps=['persons', 'billing'])
        self.add_credentials(user.role, own='*')

        source, target = self.create_orgas(user=user)

        Invoice.objects.create(
            user=self.get_root_user(), name='My Quote',
            status=InvoiceStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
        )

        response = self.assertGET200(target.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.ReceivedInvoicesBrick,
        )
        rows = self.get_brick_table_rows(brick_node)
        table_cells = self.get_alone_element(rows).findall('.//td')
        self.assertEqual(6, len(table_cells))
        self.assertEqual('?', table_cells[0].text)
        self.assertEqual('?', table_cells[1].text)
        self.assertEqual('?', table_cells[2].text)
        self.assertEqual('?', table_cells[3].text)
        self.assertEqual('?', table_cells[4].text)
        self.assertIsNone(table_cells[5].text)

    @skipIfCustomQuote
    def test_ReceivedQuotesBrick(self):
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user=user)

        response1 = self.assertGET200(target.get_absolute_url())
        brick_node1 = self.get_brick_node(
            self.get_html_tree(response1.content),
            brick=billing_bricks.ReceivedQuotesBrick,
        )
        self.assertEqual(_('Received quotes'), self.get_brick_title(brick_node1))

        # ---
        quote = Quote.objects.create(
            user=user, name='My Quote',
            status=QuoteStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
        )

        response2 = self.assertGET200(target.get_absolute_url())
        brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content),
            brick=billing_bricks.ReceivedQuotesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node2, count=1,
            title='{count} Received quote', plural_title='{count} Received quotes',
        )
        self.assertListEqual(
            [_('Name'), _('Expiration date'), _('Status'), _('Total without VAT'), _('Action')],
            self.get_brick_table_column_titles(brick_node2),
        )
        rows = self.get_brick_table_rows(brick_node2)
        table_cells = self.get_alone_element(rows).findall('.//td')
        self.assertEqual(5, len(table_cells))
        self.assertInstanceLink(table_cells[0], entity=quote)
        self.assertEqual(
            date_format(quote.expiration_date, 'DATE_FORMAT'),
            table_cells[1].text,
        )
        self.assertEqual(quote.status.name, table_cells[2].text)
        # TODO: test table_cells[3]

    @skipIfCustomQuote
    def test_ReceivedQuotesBrick__hidden_expiration(self):
        "Field 'expiration_date' is hidden."
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user=user)

        FieldsConfig.objects.create(
            content_type=Quote,
            descriptions=[
                ('expiration_date',  {FieldsConfig.HIDDEN: True}),
            ],
        )

        Quote.objects.create(
            user=user, name='My Quote',
            status=QuoteStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
        )

        response = self.assertGET200(target.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.ReceivedQuotesBrick,
        )
        self.assertListEqual(
            [_('Name'), _('Status'), _('Total without VAT'), _('Action')],
            self.get_brick_table_column_titles(brick_node),
        )
        rows = self.get_brick_table_rows(brick_node)
        row = self.get_alone_element(rows)
        self.assertEqual(4, len(row.findall('.//td')))

    @skipIfCustomQuote
    @override_settings(HIDDEN_VALUE='?')
    def test_ReceivedQuotesBrick__forbidden(self):
        "No VIEW permission."
        user = self.login_as_standard(allowed_apps=['persons', 'billing'])
        self.add_credentials(user.role, own='*')

        source, target = self.create_orgas(user=user)

        Quote.objects.create(
            user=self.get_root_user(), name='My Quote',
            status=QuoteStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
        )

        response = self.assertGET200(target.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.ReceivedQuotesBrick,
        )
        rows = self.get_brick_table_rows(brick_node)
        row = self.get_alone_element(rows)

        table_cells = row.findall('.//td')
        self.assertEqual(5, len(table_cells))
        self.assertEqual('?', table_cells[0].text)
        self.assertEqual('?', table_cells[1].text)
        self.assertEqual('?', table_cells[2].text)
        self.assertEqual('?', table_cells[3].text)
        self.assertEqual('—', table_cells[4].text)

    def test_ReceivedSalesOrdersBrick(self):
        user = self.login_as_root_and_get()
        BrickDetailviewLocation.objects.create_if_needed(
            brick=billing_bricks.ReceivedSalesOrdersBrick, order=600,
            zone=BrickDetailviewLocation.RIGHT, model=Organisation,
        )

        source, target = self.create_orgas(user=user)

        response1 = self.assertGET200(target.get_absolute_url())
        brick_node1 = self.get_brick_node(
            self.get_html_tree(response1.content),
            brick=billing_bricks.ReceivedSalesOrdersBrick,
        )
        self.assertEqual(_('Received sales orders'), self.get_brick_title(brick_node1))

        # ---
        order = SalesOrder.objects.create(
            user=user, name='My Quote',
            status=SalesOrderStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
        )

        response2 = self.assertGET200(target.get_absolute_url())
        brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content),
            brick=billing_bricks.ReceivedSalesOrdersBrick,
        )
        self.assertBrickTitleEqual(
            brick_node2,
            count=1,
            title='{count} Received sales order',
            plural_title='{count} Received sales orders',
        )
        self.assertListEqual(
            [_('Name'), _('Expiration date'), _('Status'), _('Total without VAT'), _('Action')],
            self.get_brick_table_column_titles(brick_node2),
        )
        rows = self.get_brick_table_rows(brick_node2)

        table_cells = self.get_alone_element(rows).findall('.//td')
        self.assertEqual(5, len(table_cells))
        self.assertInstanceLink(table_cells[0], entity=order)


@skipIfCustomOrganisation
class PaymentInformationBricksTestCase(BrickTestCaseMixin, _BillingTestCase):
    @skipIfCustomOrganisation
    def test_PaymentInformationBrick__managed__orga(self):
        user = self.login_as_root_and_get()

        orga = Organisation.objects.create(user=user, name='Sony', is_managed=True)
        payment_info = PaymentInformation.objects.create(organisation=orga, name='RIB sony')

        response = self.assertGET200(orga.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.PaymentInformationBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=1,
            title='{count} Payment information',
            plural_title='{count} Payments information',
        )
        self.assertBrickHasAction(
            brick_node,
            url=payment_info.get_edit_absolute_url(),
            action_type='edit',
        )

    @skipIfCustomOrganisation
    def test_PaymentInformationBrick__not_managed_brick(self):
        "Organisation is not managed."
        user = self.login_as_root_and_get()

        self.assertIs(SettingValue.objects.value_4_key(payment_info_key), True)

        orga = Organisation.objects.create(user=user, name='Sony')
        PaymentInformation.objects.create(organisation=orga, name='RIB sony')

        response = self.assertGET200(orga.get_absolute_url())
        # self.assertNoBrick(
        #     self.get_html_tree(response.content),
        #     brick_id=PaymentInformationBrick.id,
        # )
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.PaymentInformationBrick,
        )
        self.assertIn('brick-void', brick_node.attrib.get('class', ''))

    @skipIfCustomOrganisation
    def test_PaymentInformationBrick__not_managed_orga_n_displayed(self):
        "Organisation is not managed + Setting is False."
        user = self.login_as_root_and_get()

        SettingValue.objects.set_4_key(payment_info_key, False)

        orga = Organisation.objects.create(user=user, name='Sony')
        PaymentInformation.objects.create(organisation=orga, name='RIB sony')

        response = self.assertGET200(orga.get_absolute_url())
        self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.PaymentInformationBrick,
        )

    @skipIfCustomInvoice
    def test_BillingPaymentInformationBrick(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)

        create_pi = PaymentInformation.objects.create
        payment_info1 = create_pi(organisation=source, name='RIB source #1')
        payment_info2 = create_pi(organisation=source, name='RIB source #2')
        create_pi(organisation=target, name='RIB target')
        self.assertTrue(payment_info1.is_default)

        invoice = self.create_invoice(user=user, name='My invoice', source=source, target=target)
        self.assertEqual(invoice.payment_info_id, payment_info1.id)

        response = self.assertGET200(invoice.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.BillingPaymentInformationBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2,
            title='{count} Payment information',
            plural_title='{count} Payments information',
        )

        # TODO: method in base ?
        items = brick_node.findall('.//div[@class="brick-list-item billing-item"]')
        self.assertEqual(2, len(items))

        item1 = items[0]
        key_node1 = self.get_html_node_or_fail(item1, './/div[@class="billing-group-key"]')
        self.assertEqual(payment_info1.name, key_node1.text.strip())

        action_node1 = self.get_html_node_or_fail(item1, './/div[@class="billing-action"]')
        self.assertEqual(_('Selected account for this document'), action_node1.text.strip())

        item2 = items[1]
        key_node2 = self.get_html_node_or_fail(item2, './/div[@class="billing-group-key"]')
        self.assertEqual(payment_info2.name, key_node2.text.strip())

        action_node2 = self.get_html_node_or_fail(item2, './/div[@class="billing-action"]')
        self.assertBrickHasAction(
            action_node2,
            url=reverse(
                'billing__set_default_payment_info',
                args=(payment_info2.id, invoice.id),
            ),
            action_type='update',
        )

    @skipIfCustomInvoice
    def test_BillingPaymentInformationBrick__field_is_hidden(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        PaymentInformation.objects.create(organisation=source, name='RIB source')

        invoice = self.create_invoice(user=user, name='My invoice', source=source, target=target)

        FieldsConfig.objects.create(
            content_type=Invoice,
            descriptions=[('payment_info', {FieldsConfig.HIDDEN: True})],
        )

        response = self.assertGET200(invoice.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.BillingPaymentInformationBrick,
        )
        self.assertEqual(
            _('Payment information'), self.get_brick_title(brick_node),
        )


@skipIfCustomOrganisation
class AddressesBricksTestCase(BrickTestCaseMixin, _BillingTestCase):
    def _aux_adresses_brick(self, user):
        source = Organisation.objects.filter(is_managed=True)[0]
        target = Organisation.objects.create(user=user, name='Target Orga')

        create_addr = partial(Address.objects.create, owner=target)
        target.shipping_address = create_addr(
            name='ShippingAddr', address='Temple of fire',
            po_box='6565', zipcode='789', city='Konoha',
            department='dep1', state='Stuff', country='Land of Fire',
        )
        target.billing_address = create_addr(
            name='BillingAddr', address='Temple of sand',
            po_box='8778', zipcode='123', city='Suna',
            department='dep2', state='Foo', country='Land of Sand',
        )
        target.save()

        invoice = self.create_invoice(
            user=user, name='Invoice001', source=source, target=target,
        )
        self.assertAddressContentEqual(target.billing_address, invoice.billing_address)
        self.assertAddressContentEqual(target.shipping_address, invoice.shipping_address)

        return invoice

    @skipIfCustomAddress
    def test_BillingPrettyAddressBrick(self):
        user = self.login_as_root_and_get()
        invoice = self._aux_adresses_brick(user)

        response = self.assertGET200(invoice.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.BillingPrettyAddressBrick,
        )
        self.assertEqual(_('Addresses'), self.get_brick_title(brick_node))
        self.assertBrickHasAction(
            brick_node,
            url=f'{invoice.billing_address.get_edit_absolute_url()}?type=billing',
            action_type='edit',
        )
        self.assertBrickHasAction(
            brick_node,
            url=f'{invoice.shipping_address.get_edit_absolute_url()}?type=shipping',
            action_type='edit',
        )
        # TODO: complete (test content)

    @skipIfCustomAddress
    def test_BillingDetailedAddressBrick(self):
        user = self.login_as_root_and_get()
        invoice = self._aux_adresses_brick(user)

        BrickDetailviewLocation.objects.create_if_needed(
            brick=billing_bricks.BillingDetailedAddressBrick,
            order=600,
            zone=BrickDetailviewLocation.RIGHT,
            model=Invoice,
        )

        response = self.assertGET200(invoice.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.BillingDetailedAddressBrick,
        )
        self.assertEqual(_('Addresses'), self.get_brick_title(brick_node))
        self.assertBrickHasAction(
            brick_node,
            url=f'{invoice.billing_address.get_edit_absolute_url()}?type=billing',
            action_type='edit',
        )
        self.assertBrickHasAction(
            brick_node,
            url=f'{invoice.shipping_address.get_edit_absolute_url()}?type=shipping',
            action_type='edit',
        )
        # TODO: complete (test content)
