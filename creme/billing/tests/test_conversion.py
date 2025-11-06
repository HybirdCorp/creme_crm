from datetime import date, timedelta
from decimal import Decimal
from functools import partial

from django.db.models.query_utils import Q
from django.utils.timezone import now
from django.utils.translation import gettext as _

from creme.creme_core.models import (
    CremeProperty,
    CremePropertyType,
    Currency,
    Relation,
    RelationType,
)
from creme.persons.constants import REL_SUB_CUSTOMER_SUPPLIER
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

from .. import converters
from ..constants import (
    REL_SUB_BILL_ISSUED,
    REL_SUB_BILL_RECEIVED,
    REL_SUB_INVOICE_FROM_QUOTE,
)
from ..core.conversion import ConverterRegistry
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
class ConversionTestCase(_BillingTestCase):
    def test_registry(self):
        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]

        registry = ConverterRegistry()
        self.assertIsNone(
            registry.get_converter_class(source_model=Quote, target_model=Invoice),
        )
        self.assertIsNone(
            registry.get_converter(user=user, source=quote, target_model=Invoice),
        )
        self.assertFalse([*registry.models])

        registry.register(
            source_model=Quote,
            target_model=Invoice,
            converter_class=converters.QuoteToInvoiceConverter,
        )
        self.assertIs(
            registry.get_converter_class(source_model=Quote, target_model=Invoice),
            converters.QuoteToInvoiceConverter,
        )
        self.assertIsNone(
            registry.get_converter_class(source_model=Invoice, target_model=Quote),
        )
        self.assertListEqual([(Quote, Invoice)], [*registry.models])

        converter = registry.get_converter(user=user, source=quote, target_model=Invoice)
        self.assertIsInstance(converter, converters.QuoteToInvoiceConverter)
        self.assertEqual(user,    converter.user)
        self.assertEqual(quote,   converter.source)
        self.assertEqual(Invoice, converter.target_model)

        # Duplicate ---
        with self.assertRaises(ConverterRegistry.RegistrationError):
            registry.register(
                source_model=Quote,
                target_model=Invoice,
                converter_class=converters.QuoteToSalesOrderConverter,
            )

        # Unregister ---
        registry.unregister(source_model=Quote, target_model=Invoice)
        self.assertIsNone(
            registry.get_converter_class(source_model=Quote, target_model=Invoice),
        )

        with self.assertRaises(ConverterRegistry.UnRegistrationError):
            registry.unregister(source_model=Quote, target_model=Invoice)

    # TODO: test Converter.check_permissions()
    # TODO: test Converter.perform()

    @skipIfCustomAddress
    @skipIfCustomQuote
    @skipIfCustomInvoice
    def test_quote_to_invoice__addresses(self):
        "Quote -> Invoice; 2 addresses."
        user = self.login_as_root_and_get()

        def_status = InvoiceStatus.objects.create(name='OK', is_default=True)
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
        self.assertEqual(def_status,         invoice.status)
        self.assertEqual(quote.payment_info, invoice.payment_info)
        self.assertIsNone(invoice.additional_info)
        self.assertIsNone(invoice.payment_terms)

        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_ISSUED,        object=source)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_INVOICE_FROM_QUOTE, object=quote)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_RECEIVED,      object=target)
        self.assertHaveRelation(subject=target,  type=REL_SUB_CUSTOMER_SUPPLIER,  object=source)

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
    def test_quote_to_invoice__disabled_rtype(self):
        "The RelationType 'Quote -> Invoice' is disabled."
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
        self.assertHaveNoRelation(subject=invoice, type=REL_SUB_INVOICE_FROM_QUOTE, object=quote)

    @skipIfCustomQuote
    @skipIfCustomSalesOrder
    def test_quote_to_salesorder(self):
        "SalesOrder + not superuser."
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'], creatable_models=[Quote, SalesOrder],
        )
        self.add_credentials(user.role, own='*')

        def_status = SalesOrderStatus.objects.create(name='OK', is_default=True)

        source, target = self.create_orgas(user=user)
        # We set up to generate number
        self._set_managed(source)

        quote = self.create_quote(user=user, name='My Quote', source=source, target=target)
        self._convert(200, quote, 'sales_order')
        self.assertEqual(0, Invoice.objects.count())

        order = self.get_alone_element(SalesOrder.objects.all())
        # self.assertEqual('ORD1', order.number)
        self.assertStartsWith(order.number, _('ORD'))
        self.assertEqual(def_status, order.status)
        self.assertHaveNoRelation(subject=order, type=REL_SUB_INVOICE_FROM_QUOTE, object=quote)

    @skipIfCustomInvoice
    @skipIfCustomQuote
    def test_invoice_to_quote(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001')[0]

        self._convert(200, invoice, 'quote')
        self.get_alone_element(Quote.objects.all())
        # TODO: add more assertions?

    @skipIfCustomInvoice
    @skipIfCustomQuote
    def test_salesorder_to_invoice(self):
        user = self.login_as_root_and_get()
        order = self.create_salesorder_n_orgas(user=user, name='Order0001')[0]

        self._convert(200, order, 'invoice')
        self.get_alone_element(Invoice.objects.all())
        # TODO: add more assertions?

    @skipIfCustomQuote
    @skipIfCustomSalesOrder
    def test_ajax(self):
        "SalesOrder + not superuser."
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'], creatable_models=[Quote, SalesOrder],
        )
        self.add_credentials(user.role, own='*')

        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]

        response = self._convert(200, quote, 'sales_order', is_ajax=True)
        self.assertEqual(0, Invoice.objects.count())
        self.assertEqual(1, SalesOrder.objects.count())
        self.assertEqual(response.text, SalesOrder.objects.first().get_absolute_url())

    @skipIfCustomQuote
    def test_creation_forbidden(self):
        "Credentials (creation) errors."
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Quote],  # Not Invoice
        )
        self.add_credentials(user.role, own='*')

        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]
        self._convert(403, quote, 'invoice')
        self.assertFalse(Invoice.objects.exists())

    @skipIfCustomQuote
    def test_view_forbidden(self):
        "Credentials (view) errors."
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'], creatable_models=[Quote, Invoice],
        )
        self.add_credentials(user.role, own='*')

        source, target = self.create_orgas(user=user)
        quote = Quote.objects.create(
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
    def test_quote_to_invoice__lines(self):
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

        quote = self.refresh(quote)

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
        self.assertEqual(today,              invoice.issuing_date)
        self.assertEqual(today,              invoice.expiration_date)
        self.assertEqual(quote.discount,     invoice.discount)
        self.assertEqual(quote.total_no_vat, invoice.total_no_vat)
        self.assertEqual(quote.total_vat,    invoice.total_vat)

        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_ISSUED,   object=source)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_RECEIVED, object=target)

    @skipIfCustomQuote
    @skipIfCustomSalesOrder
    def test_quote_to_salesorder__status(self):
        "Quote -> SalesOrder: status id can not be converted (bugfix)."
        user = self.login_as_root_and_get()

        status = QuoteStatus.objects.create(name='Cashing', order=5)

        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]
        quote.status = status
        quote.save()

        self._convert(200, quote, 'sales_order')

        order = self.get_alone_element(SalesOrder.objects.all())
        self.assertTrue(order.status.is_default)

    @skipIfCustomQuote
    @skipIfCustomInvoice
    def test_quote_to_invoice__status(self):
        "Quote -> Invoice : status id can not be converted (bugfix)."
        user = self.login_as_root_and_get()

        pk = 1024
        self.assertFalse(InvoiceStatus.objects.filter(pk=pk).exists())

        with self.assertNoException():
            status = QuoteStatus.objects.create(pk=pk, name='Cashing', order=5)

        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]
        quote.status = status
        quote.save()

        self._convert(200, quote, 'invoice')

        invoice = self.get_alone_element(Invoice.objects.all())
        self.assertTrue(invoice.status.is_default)

    @skipIfCustomQuote
    def test_quote_to_invoice__properties(self):
        "Quote to Invoice + CremeProperties."
        user = self.login_as_root_and_get()
        quote, source, target = self.create_quote_n_orgas(user=user, name='My Quote')

        create_ptype = CremePropertyType.objects.create
        ptype1 = create_ptype(text='No constraint')
        ptype2 = create_ptype(text='Constraint')
        ptype2.set_subject_ctypes(Quote)

        create_prop = partial(CremeProperty.objects.create, creme_entity=quote)
        create_prop(type=ptype1)
        create_prop(type=ptype2)

        self._convert(200, quote, 'invoice')

        invoice = self.get_alone_element(Invoice.objects.all())
        self.assertCountEqual([ptype1], [p.type for p in invoice.properties.all()])

    @skipIfCustomQuote
    def test_quote_to_invoice__not_copiable_relations(self):
        user = self.login_as_root_and_get()
        self.assertEqual(0, Relation.objects.count())

        quote, source, target = self.create_quote_n_orgas(user=user, name='My Quote')
        rtype  = RelationType.objects.builder(
            id='test-subject_foobar', predicate='is loving', models=[Quote, Invoice],
        ).symmetric(
            id='test-object_foobar', predicate='is loved by', models=[Organisation],
        ).get_or_create()[0]
        self.assertTrue(rtype.is_copiable)
        self.assertTrue(rtype.symmetric_type.is_copiable)

        Relation.objects.create(
            user=user, type=rtype, subject_entity=quote, object_entity=source,
        )
        self.assertEqual(1, Relation.objects.filter(type=rtype).count())
        self.assertEqual(1, Relation.objects.filter(type=rtype.symmetric_type).count())

        not_copiable_rtype = RelationType.objects.builder(
            id='test-subject_foobar_not_copiable', predicate='is loving',
            models=[Quote, Invoice],
            is_copiable=False,  # <==
        ).symmetric(
            id='test-object_foobar_not_copiable', predicate='is loved by',
            models=[Organisation],
            is_copiable=False,  # <==
        ).get_or_create()[0]
        self.assertFalse(not_copiable_rtype.is_copiable)
        self.assertFalse(not_copiable_rtype.symmetric_type.is_copiable)

        Relation.objects.create(
            user=user, type=not_copiable_rtype, subject_entity=quote, object_entity=source,
        )
        self.assertEqual(1, Relation.objects.filter(type=not_copiable_rtype).count())
        self.assertEqual(
            1, Relation.objects.filter(type=not_copiable_rtype.symmetric_type).count(),
        )

        # Not compatible with Invoice
        incompatible_rtype = RelationType.objects.builder(
            id='test-subject_foobar_wrong_ctype', predicate='is loving', models=[Quote],
        ).symmetric(
            id='test-object_foobar_wrong_ctype', predicate='is loved by',
            models=[Organisation],
        ).get_or_create()[0]

        Relation.objects.create(
            user=user, type=incompatible_rtype, subject_entity=quote, object_entity=source,
        )
        self.assertEqual(1, Relation.objects.filter(type=incompatible_rtype).count())
        self.assertEqual(
            1, Relation.objects.filter(type=incompatible_rtype.symmetric_type).count()
        )

        # Contact2 < ---- > Orga
        self._convert(200, quote, 'invoice')

        filter_rtype = Relation.objects.filter
        self.assertEqual(2, filter_rtype(type=rtype).count())
        self.assertEqual(2, filter_rtype(type=rtype.symmetric_type).count())
        self.assertEqual(1, filter_rtype(type=not_copiable_rtype).count())
        self.assertEqual(1, filter_rtype(type=not_copiable_rtype.symmetric_type).count())
        self.assertEqual(1, filter_rtype(type=incompatible_rtype).count())
        self.assertEqual(1, filter_rtype(type=incompatible_rtype.symmetric_type).count())

    def test_error_invalid_source(self):
        "Source is not a billing document."
        user = self.login_as_root_and_get()
        orga = Organisation.objects.create(user=user, name='Arcadia')
        self._convert(409, orga, 'sales_order')

    def test_error_invalid_target(self):
        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]
        self._convert(409, quote, 'invalid')

    @skipIfCustomSalesOrder
    def test_error_bad_combination(self):
        "Some combinations are forbidden."
        user = self.login_as_root_and_get()
        order = self.create_salesorder_n_orgas(user=user, name='Order for Arcadia')[0]
        self._convert(409, order, 'sales_order')

    @skipIfCustomQuote
    def test_convert_deleted_entity(self):
        "Deleted entity."
        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]
        Quote.objects.filter(id=quote.id).update(is_deleted=True)
        self._convert(409, quote, 'invoice')
