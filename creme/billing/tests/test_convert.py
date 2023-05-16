from datetime import date, timedelta
from decimal import Decimal
from functools import partial

from django.db.models.query_utils import Q
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    Currency,
    Relation,
    RelationType,
    SetCredentials,
)
from creme.persons.constants import REL_SUB_CUSTOMER_SUPPLIER
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

from ..constants import (
    REL_SUB_BILL_ISSUED,
    REL_SUB_BILL_RECEIVED,
    REL_SUB_INVOICE_FROM_QUOTE,
)
from ..core import get_models_for_conversion
from ..models import (
    AdditionalInformation,
    InvoiceStatus,
    PaymentInformation,
    PaymentTerms,
    QuoteStatus,
    SalesOrderStatus,
)
from .base import (
    Address,
    Invoice,
    Organisation,
    ProductLine,
    Quote,
    SalesOrder,
    ServiceLine,
    _BillingTestCase,
    skipIfCustomInvoice,
    skipIfCustomProductLine,
    skipIfCustomQuote,
    skipIfCustomSalesOrder,
    skipIfCustomServiceLine,
)


@skipIfCustomOrganisation
class ConvertTestCase(_BillingTestCase):
    def _convert(self, status_code, src, dest_type, is_ajax=False):
        http_header = {}

        if is_ajax:
            http_header = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

        return self.assertPOST(
            status_code, reverse('billing__convert', args=(src.id,)),
            data={'type': dest_type}, follow=True, **http_header
        )

    def test_get_models_for_conversion(self):
        self.assertListEqual([], [*get_models_for_conversion('unknown')])

        self.assertListEqual([Quote, SalesOrder], [*get_models_for_conversion('invoice')])
        self.assertListEqual([], [*get_models_for_conversion('credit_note')])
        self.assertListEqual([Invoice], [*get_models_for_conversion('quote')])
        self.assertListEqual([Quote], [*get_models_for_conversion('sales_order')])

    @skipIfCustomAddress
    @skipIfCustomQuote
    @skipIfCustomInvoice
    def test_with_address(self):
        "Quote -> Invoice ; 2 addresses."
        # user = self.login()
        user = self.login_as_root_and_get()

        currency = Currency.objects.create(
            name='Berry', local_symbol='B',
            international_symbol='BB', is_custom=True,
        )

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        self._set_managed(source)
        target = create_orga(name='Target Orga')

        create_address = Address.objects.create
        target.billing_address = create_address(
            name='Billing address 01',
            address='BA1 - Address', po_box='BA1 - PO box',
            zipcode='BA1 - Zip code', city='BA1 - City',
            department='BA1 - Department',
            state='BA1 - State', country='BA1 - Country',
            owner=target,
        )
        target.shipping_address = create_address(
            name='Shipping address 01',
            address='SA1 - Address', po_box='SA1 - PO box',
            zipcode='SA1 - Zip code', city='SA1 - City',
            department='SA1 - Department',
            state='SA1 - State', country='SA1 - Country',
            owner=target,
        )
        target.save()

        address_count = Address.objects.count()

        quote = self.create_quote(
            user=user, name='My Quote', source=source, target=target, currency=currency,
        )
        self.assertTrue(quote.number)

        quote.additional_info = AdditionalInformation.objects.all()[0]
        quote.payment_terms = PaymentTerms.objects.all()[0]
        quote.payment_info = PaymentInformation.objects.create(
            organisation=source, name='Bank details', is_default=True,
        )
        quote.save()
        self.assertEqual(address_count + 2, Address.objects.count())

        quote_b_addr = quote.billing_address
        quote_b_addr.zipcode += ' (Quote)'
        quote_b_addr.save()

        quote_s_addr = quote.shipping_address
        quote_s_addr.zipcode += ' (Quote)'
        quote_s_addr.save()

        self.assertFalse(Invoice.objects.count())
        self._convert(200, quote, 'invoice')

        invoice = self.get_alone_element(Invoice.objects.all())
        self.assertEqual(
            _('{src} (converted into {dest._meta.verbose_name})').format(
                src=quote.name, dest=Invoice,
            ),
            invoice.name,
        )
        self.assertFalse(invoice.number)  # Not copied

        today = date.today()
        self.assertEqual(today, invoice.issuing_date)
        self.assertEqual(today, invoice.expiration_date)

        self.assertEqual(quote.discount,     invoice.discount)
        self.assertEqual(quote.total_vat,    invoice.total_vat)
        self.assertEqual(quote.total_no_vat, invoice.total_no_vat)
        self.assertEqual(currency,           invoice.currency)
        self.assertEqual(1,                  invoice.status_id)
        self.assertEqual(quote.payment_info, invoice.payment_info)
        self.assertIsNone(invoice.additional_info)
        self.assertIsNone(invoice.payment_terms)

        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED,        source)
        self.assertRelationCount(1, invoice, REL_SUB_INVOICE_FROM_QUOTE, quote)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED,      target)
        self.assertRelationCount(1, target,  REL_SUB_CUSTOMER_SUPPLIER,  source)

        # Addresses are cloned
        self.assertEqual(address_count + 4, Address.objects.count())

        billing_address = invoice.billing_address
        self.assertIsInstance(billing_address, Address)
        self.assertEqual(invoice,              billing_address.owner)
        self.assertEqual(quote_b_addr.name,    billing_address.name)
        self.assertEqual(quote_b_addr.city,    billing_address.city)
        self.assertEqual(quote_b_addr.zipcode, billing_address.zipcode)

        shipping_address = invoice.shipping_address
        self.assertIsInstance(shipping_address, Address)
        self.assertEqual(invoice,                 shipping_address.owner)
        self.assertEqual(quote_s_addr.name,       shipping_address.name)
        self.assertEqual(quote_s_addr.department, shipping_address.department)
        self.assertEqual(quote_s_addr.zipcode,    shipping_address.zipcode)

    @skipIfCustomQuote
    @skipIfCustomInvoice
    def test_disabled_rtype(self):
        "The RelationType 'Quote -> Invoice' is disabled."
        # user = self.login()
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        quote = self.create_quote(user=user, name='My Quote', source=source, target=target)

        rtype = RelationType.objects.get(id=REL_SUB_INVOICE_FROM_QUOTE)
        rtype.enabled = False
        rtype.save()

        try:
            self._convert(200, quote, 'invoice')
        finally:
            rtype.enabled = True
            rtype.save()

        invoice = self.get_alone_element(Invoice.objects.all())
        self.assertRelationCount(0, invoice, REL_SUB_INVOICE_FROM_QUOTE, quote)

    @skipIfCustomQuote
    @skipIfCustomSalesOrder
    @override_settings(SALESORDER_NUMBER_PREFIX='ORD')
    def test_not_super_user(self):
        "SalesOrder + not superuser."
        # user = self.login(is_superuser=False, allowed_apps=['billing', 'persons'])
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'], creatable_models=[Quote, SalesOrder],
        )
        SetCredentials.objects.create(
            role=user.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        source, target = self.create_orgas(user=user)
        # We set up to generate number
        self._set_managed(source)

        quote = self.create_quote(user=user, name='My Quote', source=source, target=target)
        self._convert(200, quote, 'sales_order')
        self.assertEqual(0, Invoice.objects.count())

        order = self.get_alone_element(SalesOrder.objects.all())
        self.assertEqual('ORD1', order.number)
        self.assertRelationCount(0, order, REL_SUB_INVOICE_FROM_QUOTE, quote)

    @skipIfCustomQuote
    @skipIfCustomSalesOrder
    def test_ajax(self):
        "SalesOrder + not superuser."
        # user = self.login(is_superuser=False, allowed_apps=['billing', 'persons'])
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'], creatable_models=[Quote, SalesOrder],
        )
        SetCredentials.objects.create(
            role=user.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]

        response = self._convert(200, quote, 'sales_order', is_ajax=True)
        self.assertEqual(0, Invoice.objects.count())
        self.assertEqual(1, SalesOrder.objects.count())

        self.assertEqual(
            force_str(response.content),
            SalesOrder.objects.first().get_absolute_url(),
        )

    @skipIfCustomQuote
    def test_creation_forbidden(self):
        "Credentials (creation) errors."
        # user = self.login(is_superuser=False, allowed_apps=['billing', 'persons'])
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Quote],  # Not Invoice
        )
        SetCredentials.objects.create(
            role=user.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]
        self._convert(403, quote, 'invoice')
        self.assertFalse(Invoice.objects.exists())

    @skipIfCustomQuote
    def test_view_forbidden(self):
        "Credentials (view) errors."
        # user = self.login(is_superuser=False, allowed_apps=['billing', 'persons'])
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'], creatable_models=[Quote, Invoice],
        )
        SetCredentials.objects.create(
            role=user.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        source, target = self.create_orgas(user=user)
        quote = Quote.objects.create(
            # user=self.other_user, name='My Quote',
            user=self.get_root_user(), name='My Quote',
            issuing_date=now(),
            expiration_date=now() + timedelta(days=10),
            status=QuoteStatus.objects.all()[0],
            source=source,
            target=target,
        )
        self.assertFalse(user.has_perm_to_view(quote))

        self._convert(403, quote, 'invoice')
        self.assertFalse(Invoice.objects.exists())

    @skipIfCustomQuote
    @skipIfCustomInvoice
    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_with_lines(self):
        "Quote to Invoice with lines."
        # user = self.login()
        user = self.login_as_root_and_get()
        quote, source, target = self.create_quote_n_orgas(user=user, name='My Quote')

        create_pline = partial(
            ProductLine.objects.create, user=user, related_document=quote,
        )
        product_line_otf = create_pline(
            on_the_fly_item='otf1', unit_price=Decimal('1'),
        )
        product_line = create_pline(
            related_item=self.create_product(user=user), unit_price=Decimal('2'),
        )

        create_sline = partial(
            ServiceLine.objects.create, user=user, related_document=quote,
        )
        service_line_otf = create_sline(
            on_the_fly_item='otf2', unit_price=Decimal('4'),
        )
        service_line = create_sline(
            related_item=self.create_service(user=user), unit_price=Decimal('5'),
        )

        # quote.save() # To set total_vat...
        quote = self.refresh(quote)

        ptype = CremePropertyType.objects.smart_update_or_create(
            str_pk='billing-prtest_convert05', text='Test',
        )
        quote_property = CremeProperty.objects.create(creme_entity=quote, type=ptype)

        self.assertEqual(2, quote.get_lines(ServiceLine).count())
        self.assertEqual(2, quote.get_lines(ProductLine).count())

        self.assertFalse(Invoice.objects.exists())

        self._convert(200, quote, 'invoice')

        invoice = self.get_alone_element(Invoice.objects.all())
        self.assertEqual(2, invoice.get_lines(ServiceLine).count())
        self.assertEqual(2, invoice.get_lines(ProductLine).count())

        q_otf_item = Q(on_the_fly_item=None)
        # Should be with the related_item
        invoice_service_line     = invoice.get_lines(ServiceLine).get(q_otf_item)
        invoice_service_line_otf = invoice.get_lines(ServiceLine).get(~q_otf_item)

        self.assertEqual(service_line.related_item,     invoice_service_line.related_item)
        self.assertEqual(service_line_otf.related_item, invoice_service_line_otf.related_item)

        # Should be with the related_item
        invoice_product_line     = invoice.get_lines(ProductLine).get(q_otf_item)
        invoice_product_line_otf = invoice.get_lines(ProductLine).get(~q_otf_item)

        self.assertEqual(product_line.related_item,     invoice_product_line.related_item)
        self.assertEqual(product_line_otf.related_item, invoice_product_line_otf.related_item)

        today = date.today()
        self.assertEqual(today,                 invoice.issuing_date)
        self.assertEqual(today,                 invoice.expiration_date)
        self.assertEqual(quote.discount,        invoice.discount)
        self.assertEqual(quote.total_no_vat,    invoice.total_no_vat)
        self.assertEqual(quote.total_vat,       invoice.total_vat)

        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED, target)

        self.assertCountEqual(
            [quote_property.type_id],
            invoice.properties.values_list('type', flat=True),
        )

    @skipIfCustomQuote
    @skipIfCustomSalesOrder
    def test_status01(self):
        "Quote -> SalesOrder: status id can not be converted (bugfix)."
        # user = self.login()
        user = self.login_as_root_and_get()

        status = QuoteStatus.objects.create(name='Cashing', order=5)
        self.assertFalse(SalesOrderStatus.objects.filter(pk=status.pk).exists())

        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]
        quote.status = status
        quote.save()

        self._convert(200, quote, 'sales_order')

        order = self.get_alone_element(SalesOrder.objects.all())
        self.assertEqual(1, order.status_id)

    @skipIfCustomQuote
    @skipIfCustomInvoice
    def test_status02(self):
        "Quote -> Invoice : status id can not be converted (bugfix)."
        # user = self.login()
        user = self.login_as_root_and_get()

        pk = 12
        self.assertFalse(InvoiceStatus.objects.filter(pk=pk).exists())

        with self.assertNoException():
            status = QuoteStatus.objects.create(pk=pk, name='Cashing', order=5)

        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]
        quote.status = status
        quote.save()

        self._convert(200, quote, 'invoice')

        invoice = self.get_alone_element(Invoice.objects.all())
        self.assertEqual(1, invoice.status_id)

    @skipIfCustomQuote
    def test_not_copiable_relations(self):
        # user = self.login()
        user = self.login_as_root_and_get()
        self.assertEqual(0, Relation.objects.count())

        quote, source, target = self.create_quote_n_orgas(user=user, name='My Quote')
        rtype1, rtype2 = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar', 'is loving',   (Quote, Invoice)),
            ('test-object_foobar',  'is loved by', (Organisation,)),
        )

        self.assertTrue(rtype1.is_copiable)
        self.assertTrue(rtype2.is_copiable)

        Relation.objects.create(
            user=user, type=rtype1, subject_entity=quote, object_entity=source,
        )
        self.assertEqual(1, Relation.objects.filter(type=rtype1).count())
        self.assertEqual(1, Relation.objects.filter(type=rtype2).count())

        rtype3, rtype4 = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar_not_copiable', 'is loving', (Quote, Invoice)),
            ('test-object_foobar_not_copiable',  'is loved by', (Organisation,)),
            is_copiable=False,
        )
        self.assertFalse(rtype3.is_copiable)
        self.assertFalse(rtype4.is_copiable)

        Relation.objects.create(
            user=user, type=rtype3, subject_entity=quote, object_entity=source,
        )
        self.assertEqual(1, Relation.objects.filter(type=rtype3).count())
        self.assertEqual(1, Relation.objects.filter(type=rtype4).count())

        rtype5, rtype6 = RelationType.objects.smart_update_or_create(
            ('test-subject_foobar_wrong_ctype', 'is loving',   (Quote,)),
            ('test-object_foobar_wrong_ctype',  'is loved by', (Organisation,)),
        )

        Relation.objects.create(
            user=user, type=rtype5, subject_entity=quote, object_entity=source,
        )
        self.assertEqual(1, Relation.objects.filter(type=rtype5).count())
        self.assertEqual(1, Relation.objects.filter(type=rtype6).count())

        # Contact2 < ---- > Orga
        self._convert(200, quote, 'invoice')
        self.assertEqual(2, Relation.objects.filter(type=rtype1).count())
        self.assertEqual(2, Relation.objects.filter(type=rtype2).count())
        self.assertEqual(1, Relation.objects.filter(type=rtype3).count())
        self.assertEqual(1, Relation.objects.filter(type=rtype4).count())
        self.assertEqual(1, Relation.objects.filter(type=rtype5).count())
        self.assertEqual(1, Relation.objects.filter(type=rtype6).count())

    @skipIfCustomQuote
    def test_converted_relations(self):
        # user = self.login()
        user = self.login_as_root_and_get()
        from ..registry import relationtype_converter

        self.assertEqual(0, Relation.objects.count())
        quote, source, target = self.create_quote_n_orgas(user=user, name='My Quote')
        rtype1, rtype2 = RelationType.objects.smart_update_or_create(
            ('test-CONVERT-subject_foobar', 'is loving',   [Quote]),
            ('test-CONVERT-object_foobar',  'is loved by', [Organisation]),
        )
        rtype3, rtype4 = RelationType.objects.smart_update_or_create(
            ('test-CONVERT-subject_foobar_not_copiable', 'is loving', [Invoice]),
            ('test-CONVERT-object_foobar_not_copiable',  'is loved by', [Organisation]),
        )
        relationtype_converter.register(Quote, rtype1, Invoice, rtype3)

        Relation.objects.create(
            user=user, type=rtype1, subject_entity=quote, object_entity=source,
        )
        self.assertEqual(1, Relation.objects.filter(type=rtype1).count())
        self.assertEqual(1, Relation.objects.filter(type=rtype2).count())
        self.assertEqual(0, Relation.objects.filter(type=rtype3).count())
        self.assertEqual(0, Relation.objects.filter(type=rtype4).count())

        self._convert(200, quote, 'invoice')
        self.assertEqual(1, Relation.objects.filter(type=rtype1).count())
        self.assertEqual(1, Relation.objects.filter(type=rtype2).count())
        self.assertEqual(1, Relation.objects.filter(type=rtype3).count())
        self.assertEqual(1, Relation.objects.filter(type=rtype4).count())

    @skipIfCustomOrganisation
    def test_error_invalid_source(self):
        "Source is not a billing document."
        # user = self.login()
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='Arcadia')
        self._convert(409, orga, 'sales_order')

    @skipIfCustomSalesOrder
    def test_error_bad_combination(self):
        "Some combinations are forbidden."
        # user = self.login()
        user = self.login_as_root_and_get()
        order = self.create_salesorder_n_orgas(user=user, name='Order for Arcadia')[0]
        self._convert(409, order, 'sales_order')

    @skipIfCustomQuote
    def test_convert_deleted_entity(self):
        "Deleted entity."
        # user = self.login()
        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]
        Quote.objects.filter(id=quote.id).update(is_deleted=True)
        self._convert(409, quote, 'invoice')
