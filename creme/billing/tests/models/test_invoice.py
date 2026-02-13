from decimal import Decimal
from functools import partial

from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.template import Context, Template
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.billing import bricks as billing_bricks
from creme.billing.constants import (
    REL_SUB_BILL_ISSUED,
    REL_SUB_BILL_RECEIVED,
    UUID_INVOICE_STATUS_DRAFT,
    UUID_INVOICE_STATUS_TO_BE_SENT,
)
from creme.billing.models import (
    AdditionalInformation,
    InvoiceStatus,
    Line,
    PaymentTerms,
)
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import (
    CremeEntity,
    Currency,
    Relation,
    RelationType,
    Vat,
)
from creme.creme_core.tests.base import CremeTransactionTestCase
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils import currency_format
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)
from creme.products.tests.base import skipIfCustomProduct

from ..base import (
    Address,
    Invoice,
    Organisation,
    ProductLine,
    ServiceLine,
    _BillingTestCase,
    _BillingTestCaseMixin,
    skipIfCustomInvoice,
    skipIfCustomProductLine,
    skipIfCustomServiceLine,
)


class InvoiceStatusTestCase(_BillingTestCase):
    def test_default(self):
        statuses = [*InvoiceStatus.objects.all()]
        self.assertEqual(8, len(statuses))

        default_status = self.get_alone_element(
            [status for status in statuses if status.is_default]
        )
        self.assertUUIDEqual(UUID_INVOICE_STATUS_DRAFT, default_status.uuid)

        # New default status => previous default status is updated
        new_status1 = InvoiceStatus.objects.create(name='OK', is_default=True)
        self.assertTrue(self.refresh(new_status1).is_default)
        self.assertEqual(9, InvoiceStatus.objects.count())
        self.assertFalse(
            InvoiceStatus.objects.exclude(id=new_status1.id).filter(is_default=True)
        )

        # No default status is found => new one is default one
        InvoiceStatus.objects.update(is_default=False)
        new_status2 = InvoiceStatus.objects.create(name='KO', is_default=False)
        self.assertTrue(self.refresh(new_status2).is_default)

    def test_validated(self):
        statuses = [*InvoiceStatus.objects.all()]
        self.assertEqual(8, len(statuses))

        validated_status = self.get_alone_element(
            [status for status in statuses if status.is_validated]
        )
        self.assertUUIDEqual(UUID_INVOICE_STATUS_TO_BE_SENT, validated_status.uuid)

        # New validated status => previous validated status is updated
        new_status1 = InvoiceStatus.objects.create(name='OK', is_validated=True)
        self.assertTrue(self.refresh(new_status1).is_validated)
        self.assertEqual(9, InvoiceStatus.objects.count())
        self.assertFalse(
            InvoiceStatus.objects.exclude(id=new_status1.id).filter(is_validated=True)
        )

        # No default status is found => new one is default one
        InvoiceStatus.objects.update(is_validated=False)
        new_status2 = InvoiceStatus.objects.create(name='KO', is_validated=False)
        self.assertTrue(self.refresh(new_status2).is_validated)

    def test_render(self):
        user = self.get_root_user()
        status = InvoiceStatus.objects.create(name='OK', color='00FF00')
        invoice = Invoice(user=user, name='OK Invoice', status=status)

        with self.assertNoException():
            render = Template(
                r'{% load creme_core_tags %}'
                r'{% print_field object=invoice field="status" tag=tag %}'
            ).render(Context({
                'user': user,
                'invoice': invoice,
                'tag': ViewTag.HTML_DETAIL,
            }))

        self.assertHTMLEqual(
            f'<div class="ui-creme-colored_status">'
            f' <div class="ui-creme-color_indicator" style="background-color:#{status.color};" />'
            f' <span>{status.name}</span>'
            f'</div>',
            render,
        )


@skipIfCustomOrganisation
@skipIfCustomInvoice
class InvoiceTestCase(BrickTestCaseMixin, _BillingTestCase):
    def test_source_n_target__creation(self):
        user = self.login_as_root_and_get()
        name = 'Invoice001'
        source, target = self.create_orgas(user=user)
        invoice = Invoice.objects.create(
            user=user,
            name=name,
            status=self.get_object_or_fail(InvoiceStatus, is_default=True),
            source=source,
            target=target,
        )
        self.assertEqual(user, invoice.user)
        self.assertEqual(name, invoice.name)
        self.assertTrue(invoice.status.is_default)

        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_ISSUED,   object=source)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_RECEIVED, object=target)

        with self.assertNumQueries(0):
            gotten_source = invoice.source

        with self.assertNumQueries(0):
            gotten_target = invoice.target

        self.assertEqual(source, gotten_source)
        self.assertEqual(target, gotten_target)

        # TODO: move to test_bricks
        response = self.assertGET200(invoice.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=billing_bricks.TargetBrick,
        )
        self.assertInstanceLink(brick_node, source)
        self.assertInstanceLink(brick_node, target)

    def test_source_n_target__errors(self):
        "Errors at creation."
        user = self.get_root_user()
        source, target = self.create_orgas(user=user)

        build_invoice = partial(
            Invoice, user=user, name='Invoice001',
            status=self.get_object_or_fail(InvoiceStatus, is_default=True),
        )

        invoice1 = build_invoice(source=source)  # target=target
        msg1 = _('Target is required.')
        with self.assertRaises(ValidationError) as cm1:
            invoice1.clean()
        self.assertEqual(msg1, cm1.exception.message)

        with self.assertRaises(ValidationError) as cm2:
            invoice1.save()
        self.assertEqual(msg1, cm2.exception.message)

        invoice2 = build_invoice(target=target)  # source=source
        msg2 = _('Source organisation is required.')
        with self.assertRaises(ValidationError) as cm3:
            invoice2.clean()
        self.assertEqual(msg2, cm3.exception.message)

        with self.assertRaises(ValidationError) as cm4:
            invoice2.save()
        self.assertEqual(msg2, cm4.exception.message)

    def test_source_n_target__edition(self):
        user = self.get_root_user()
        name = 'Invoice001'
        source1, target1 = self.create_orgas(user=user)
        invoice = Invoice.objects.create(
            user=user,
            name=name,
            status=self.get_object_or_fail(InvoiceStatus, is_default=True),
            source=source1,
            target=target1,
        )
        source2, target2 = self.create_orgas(user=user, index=2)

        # ---
        invoice = self.refresh(invoice)

        invoice.source = source2
        invoice.save()

        self.assertHaveNoRelation(subject=invoice, type=REL_SUB_BILL_ISSUED, object=source1)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_ISSUED, object=source2)

        # ---
        invoice = self.refresh(invoice)

        invoice.target = target2
        invoice.save()

        self.assertHaveNoRelation(subject=invoice, type=REL_SUB_BILL_RECEIVED, object=target1)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_RECEIVED, object=target2)

    def test_source_n_target__several_saves(self):
        "Several save without refreshing."
        user = self.get_root_user()
        name = 'invoice001'
        source1, target1 = self.create_orgas(user=user)
        invoice = Invoice.objects.create(
            user=user,
            name=name,
            status=self.get_object_or_fail(InvoiceStatus, is_default=True),
            source=source1,
            target=target1,
        )

        # ---
        source2, target2 = self.create_orgas(user=user, index=2)
        invoice.source = source2
        invoice.target = target2
        invoice.save()

        self.assertHaveNoRelation(invoice, REL_SUB_BILL_ISSUED, source1)
        self.assertHaveRelation(invoice, REL_SUB_BILL_ISSUED, source2)

        self.assertHaveNoRelation(invoice, REL_SUB_BILL_RECEIVED, target1)
        self.assertHaveRelation(invoice, REL_SUB_BILL_RECEIVED, target2)

        # ---
        source3, target3 = self.create_orgas(user=user, index=3)
        invoice.source = source3
        invoice.target = target3
        invoice.save()

        self.assertHaveNoRelation(invoice, REL_SUB_BILL_ISSUED, source2)
        self.assertHaveRelation(invoice, REL_SUB_BILL_ISSUED, source3)

        self.assertHaveNoRelation(invoice, REL_SUB_BILL_RECEIVED, target2)
        self.assertHaveRelation(invoice, REL_SUB_BILL_RECEIVED, target3)

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_get_lines(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        self.assertFalse(invoice.get_lines(ProductLine))
        self.assertFalse(invoice.get_lines(ServiceLine))

        kwargs = {'user': user, 'related_document': invoice}
        product_line = ProductLine.objects.create(on_the_fly_item='Flyyy product', **kwargs)
        service_line = ServiceLine.objects.create(on_the_fly_item='Flyyy service', **kwargs)

        self.assertListEqual(
            [product_line.pk],
            [*invoice.get_lines(ProductLine).values_list('pk', flat=True)],
        )
        self.assertListEqual(
            [service_line.pk],
            [*invoice.get_lines(ServiceLine).values_list('pk', flat=True)],
        )

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_get_lines__cache(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        kwargs = {'user': user, 'related_document': invoice}

        # ----
        product_line = ProductLine.objects.create(on_the_fly_item='Flyyy product', **kwargs)
        plines = [*invoice.get_lines(ProductLine)]

        self.assertEqual([product_line], plines)

        with self.assertNumQueries(0):
            [*invoice.get_lines(ProductLine)]  # NOQA

        # ----
        service_line = ServiceLine.objects.create(on_the_fly_item='Flyyy service', **kwargs)
        slines1 = [*invoice.get_lines(ServiceLine)]

        self.assertEqual([service_line], slines1)

        with self.assertNumQueries(0):
            slines2 = [*invoice.get_lines(ServiceLine)]
        self.assertEqual([service_line], slines2)

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_iter_all_lines(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]

        kwargs = {'user': user, 'related_document': invoice}
        product_line = ProductLine.objects.create(on_the_fly_item='Flyyy product', **kwargs)
        service_line = ServiceLine.objects.create(on_the_fly_item='Flyyy service', **kwargs)

        self.assertListEqual(
            [product_line, service_line],
            [*invoice.iter_all_lines()],
        )

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_total_vat(self):
        user = self.login_as_root_and_get()

        vat = self.get_object_or_fail(Vat, value='0.0')

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        self.assertEqual(0, invoice._get_total_with_tax())

        kwargs = {'user': user, 'related_document': invoice, 'vat_value': vat}
        product_line = ProductLine.objects.create(
            on_the_fly_item='Flyyy product', quantity=3, unit_price=Decimal('5'),
            **kwargs
        )
        expected = product_line.get_price_inclusive_of_tax()
        self.assertEqual(Decimal('15.00'), expected)

        invoice.save()
        invoice = self.refresh(invoice)
        self.assertEqual(expected, invoice._get_total_with_tax())
        self.assertEqual(expected, invoice.total_vat)

        service_line = ServiceLine.objects.create(
            on_the_fly_item='Flyyy service', quantity=9, unit_price=Decimal("10"),
            **kwargs
        )
        expected = (
            product_line.get_price_inclusive_of_tax()
            + service_line.get_price_inclusive_of_tax()
        )
        invoice.save()
        invoice = self.refresh(invoice)
        self.assertEqual(expected, invoice._get_total_with_tax())
        self.assertEqual(expected, invoice.total_vat)

        # TODO: move to test_bricks
        response = self.assertGET200(invoice.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=billing_bricks.TotalBrick,
        )

        exc_total_node = self.get_html_node_or_fail(
            brick_node, './/h1[@name="total_no_vat"]'
        )
        self.assertIn(
            currency_format.currency(invoice.total_no_vat, invoice.currency),
            exc_total_node.text,
        )

        inc_total_node = self.get_html_node_or_fail(
            brick_node, './/h1[@name="total_vat"]'
        )
        self.assertIn(
            currency_format.currency(invoice.total_vat, invoice.currency),
            inc_total_node.text,
        )

    @skipIfCustomAddress
    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_clone(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        create_address = Address.objects.create
        target.billing_address = create_address(
            name='Billing address 01', address='BA1 - Address',
            po_box='BA1 - PO box', zipcode='BA1 - Zip code',
            city='BA1 - City', department='BA1 - Department',
            state='BA1 - State', country='BA1 - Country',
            owner=target,
        )
        target.shipping_address = create_address(
            name='Shipping address 01', address='SA1 - Address',
            po_box='SA1 - PO box', zipcode='SA1 - Zip code',
            city='SA1 - City', department='SA1 - Department',
            state='SA1 - State', country='SA1 - Country',
            owner=target,
        )
        target.save()

        address_count = Address.objects.count()

        default_status = self.get_object_or_fail(InvoiceStatus, is_default=True)
        currency = Currency.objects.create(
            name='Martian dollar', local_symbol='M$',
            international_symbol='MUSD', is_custom=True,
        )
        invoice = self.create_invoice(
            user=user, name='Invoice001',
            source=source, target=target,
            currency=currency,
            status=InvoiceStatus.objects.filter(is_default=False).first(),
        )
        invoice.additional_info = AdditionalInformation.objects.all()[0]
        invoice.payment_terms = PaymentTerms.objects.all()[0]
        invoice.number = 'INV1235'
        invoice.save()

        kwargs = {'user': user, 'related_document': invoice}
        ServiceLine.objects.create(related_item=self.create_service(user=user), **kwargs)
        ServiceLine.objects.create(on_the_fly_item='otf service', **kwargs)
        ProductLine.objects.create(related_item=self.create_product(user=user), **kwargs)
        ProductLine.objects.create(on_the_fly_item='otf product', **kwargs)

        self.assertEqual(address_count + 2, Address.objects.count())

        origin_b_addr = invoice.billing_address
        origin_b_addr.zipcode += ' (edited)'
        origin_b_addr.save()

        origin_s_addr = invoice.shipping_address
        origin_s_addr.zipcode += ' (edited)'
        origin_s_addr.save()

        cloned = self.clone(invoice)

        self.assertNotEqual(invoice, cloned)  # Not the same pk
        self.assertEqual(invoice.name,   cloned.name)
        self.assertEqual(currency,       cloned.currency)
        self.assertEqual(default_status, cloned.status)
        self.assertIsNone(cloned.additional_info)  # Should not be cloned
        self.assertIsNone(cloned.payment_terms)    # Should not be cloned
        self.assertEqual(source, cloned.source)
        self.assertEqual(target, cloned.target)
        self.assertEqual('',     cloned.number)

        # Lines are cloned
        src_line_ids = [line.id for line in invoice.iter_all_lines()]
        self.assertEqual(4, len(src_line_ids))

        cloned_line_ids = [line.id for line in cloned.iter_all_lines()]
        self.assertEqual(4, len(cloned_line_ids))

        self.assertFalse({*src_line_ids} & {*cloned_line_ids})

        # Addresses are cloned
        self.assertEqual(address_count + 4, Address.objects.count())

        billing_address = cloned.billing_address
        self.assertIsInstance(billing_address, Address)
        self.assertEqual(cloned,                billing_address.owner)
        self.assertEqual(origin_b_addr.name,    billing_address.name)
        self.assertEqual(origin_b_addr.city,    billing_address.city)
        self.assertEqual(origin_b_addr.zipcode, billing_address.zipcode)

        shipping_address = cloned.shipping_address
        self.assertIsInstance(shipping_address, Address)
        self.assertEqual(cloned,                   shipping_address.owner)
        self.assertEqual(origin_s_addr.name,       shipping_address.name)
        self.assertEqual(origin_s_addr.department, shipping_address.department)
        self.assertEqual(origin_s_addr.zipcode,    shipping_address.zipcode)

    # @skipIfCustomAddress
    # @skipIfCustomProductLine
    # @skipIfCustomServiceLine
    # def test_clone__method(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #
    #     create_orga = partial(Organisation.objects.create, user=user)
    #     source = create_orga(name='Source Orga')
    #     target = create_orga(name='Target Orga')
    #
    #     create_address = Address.objects.create
    #     target.billing_address = create_address(
    #         name='Billing address 01', address='BA1 - Address',
    #         po_box='BA1 - PO box', zipcode='BA1 - Zip code',
    #         city='BA1 - City', department='BA1 - Department',
    #         state='BA1 - State', country='BA1 - Country',
    #         owner=target,
    #     )
    #     target.shipping_address = create_address(
    #         name='Shipping address 01', address='SA1 - Address',
    #         po_box='SA1 - PO box', zipcode='SA1 - Zip code',
    #         city='SA1 - City', department='SA1 - Department',
    #         state='SA1 - State', country='SA1 - Country',
    #         owner=target,
    #     )
    #     target.save()
    #
    #     address_count = Address.objects.count()
    #
    #     default_status = self.get_object_or_fail(InvoiceStatus, is_default=True)
    #     currency = Currency.objects.create(
    #         name='Martian dollar', local_symbol='M$',
    #         international_symbol='MUSD', is_custom=True,
    #     )
    #     invoice = self.create_invoice(
    #         user=user, name='Invoice001',
    #         source=source, target=target,
    #         currency=currency,
    #         status=InvoiceStatus.objects.filter(is_default=False).first(),
    #     )
    #     invoice.additional_info = AdditionalInformation.objects.all()[0]
    #     invoice.payment_terms = PaymentTerms.objects.all()[0]
    #     invoice.save()
    #
    #     kwargs = {'user': user, 'related_document': invoice}
    #     ServiceLine.objects.create(related_item=self.create_service(user=user), **kwargs)
    #     ServiceLine.objects.create(on_the_fly_item='otf service', **kwargs)
    #     ProductLine.objects.create(related_item=self.create_product(user=user), **kwargs)
    #     ProductLine.objects.create(on_the_fly_item='otf product', **kwargs)
    #
    #     self.assertEqual(address_count + 2, Address.objects.count())
    #
    #     origin_b_addr = invoice.billing_address
    #     origin_b_addr.zipcode += ' (edited)'
    #     origin_b_addr.save()
    #
    #     origin_s_addr = invoice.shipping_address
    #     origin_s_addr.zipcode += ' (edited)'
    #     origin_s_addr.save()
    #
    #     cloned = self.refresh(invoice.clone())
    #     invoice = self.refresh(invoice)
    #
    #     self.assertNotEqual(invoice, cloned)  # Not the same pk
    #     self.assertEqual(invoice.name,   cloned.name)
    #     self.assertEqual(currency,       cloned.currency)
    #     self.assertEqual(default_status, cloned.status)
    #     self.assertIsNone(cloned.additional_info)  # Should not be cloned
    #     self.assertIsNone(cloned.payment_terms)    # Should not be cloned
    #     self.assertEqual(source, cloned.source)
    #     self.assertEqual(target, cloned.target)
    #     self.assertEqual('',     cloned.number)
    #
    #     # Lines are cloned
    #     src_line_ids = [line.id for line in invoice.iter_all_lines()]
    #     self.assertEqual(4, len(src_line_ids))
    #
    #     cloned_line_ids = [line.id for line in cloned.iter_all_lines()]
    #     self.assertEqual(4, len(cloned_line_ids))
    #
    #     self.assertFalse({*src_line_ids} & {*cloned_line_ids})
    #
    #     # Addresses are cloned
    #     self.assertEqual(address_count + 4, Address.objects.count())
    #
    #     billing_address = cloned.billing_address
    #     self.assertIsInstance(billing_address, Address)
    #     self.assertEqual(cloned,                billing_address.owner)
    #     self.assertEqual(origin_b_addr.name,    billing_address.name)
    #     self.assertEqual(origin_b_addr.city,    billing_address.city)
    #     self.assertEqual(origin_b_addr.zipcode, billing_address.zipcode)
    #
    #     shipping_address = cloned.shipping_address
    #     self.assertIsInstance(shipping_address, Address)
    #     self.assertEqual(cloned,                   shipping_address.owner)
    #     self.assertEqual(origin_s_addr.name,       shipping_address.name)
    #     self.assertEqual(origin_s_addr.department, shipping_address.department)
    #     self.assertEqual(origin_s_addr.zipcode,    shipping_address.zipcode)
    #
    # def test_clone__method__source_n_target(self):  # DEPRECATED
    #     "Internal relation-types should not be cloned."
    #     user = self.login_as_root_and_get()
    #
    #     invoice, source, target = self.create_invoice_n_orgas(user=user, name='Invoice001')
    #     cloned_source = source.clone()
    #     cloned_target = target.clone()
    #
    #     self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_ISSUED,   object=source)
    #     self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_RECEIVED, object=target)
    #     self.assertHaveNoRelation(invoice, type=REL_SUB_BILL_ISSUED,   object=cloned_source)
    #     self.assertHaveNoRelation(invoice, type=REL_SUB_BILL_RECEIVED, object=cloned_target)

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_discounts(self):
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=10)[0]

        kwargs = {'user': user, 'related_document': invoice}
        product_line = ProductLine.objects.create(
            on_the_fly_item='Flyyy product',
            unit_price=Decimal('1000.00'), quantity=2,
            discount=Decimal('10.00'),
            discount_unit=Line.Discount.PERCENT,
            vat_value=Vat.objects.default(),
            **kwargs
        )
        self.assertEqual(1620, product_line.get_price_exclusive_of_tax())

        invoice = self.refresh(invoice)
        self.assertEqual(1620, invoice._get_total())
        self.assertEqual(1620, invoice.total_no_vat)

        service_line = ServiceLine.objects.create(
            on_the_fly_item='Flyyy service',
            unit_price=Decimal('20.00'), quantity=10,
            discount=Decimal('100.00'),
            discount_unit=Line.Discount.LINE_AMOUNT,
            vat_value=Vat.objects.default(),
            **kwargs
        )
        self.assertEqual(90, service_line.get_price_exclusive_of_tax())

        invoice = self.refresh(invoice)
        self.assertEqual(1710, invoice._get_total())  # total_exclusive_of_tax
        self.assertEqual(1710, invoice.total_no_vat)

    def test_delete(self):
        user = self.login_as_root_and_get()
        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Nerv')

        kwargs = {
            'user': user, 'related_document': invoice,
            'unit_price': Decimal('1000.00'), 'quantity': 2,
            'discount': Decimal('10.00'),
            'discount_unit': Line.Discount.PERCENT,
            'vat_value': Vat.objects.default(),
        }
        product_line = ProductLine.objects.create(
            on_the_fly_item='Flyyy product', **kwargs
        )
        service_line = ServiceLine.objects.create(
            on_the_fly_item='Flyyy service', **kwargs
        )

        url = invoice.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            invoice = self.refresh(invoice)

        self.assertIs(invoice.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(invoice)
        self.assertDoesNotExist(product_line)
        self.assertDoesNotExist(service_line)
        self.assertStillExists(source)
        self.assertStillExists(target)

    @skipIfCustomProduct
    def test_delete__linked_product(self):
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Nerv')[0]
        product = self.create_product(user=user, name='EVA')
        product_line = ProductLine.objects.create(
            # on_the_fly_item='Flyyy product',
            related_item=product,
            user=user,
            related_document=invoice,
            unit_price=Decimal('1000.00'),
            quantity=2,
            discount=Decimal('10.00'),
            discount_unit=Line.Discount.PERCENT,
            vat_value=Vat.objects.default(),
        )

        url = invoice.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            invoice = self.refresh(invoice)

        self.assertIs(invoice.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(invoice)
        self.assertDoesNotExist(product_line)

    def test_delete_status(self):
        user = self.login_as_root_and_get()

        new_status = InvoiceStatus.objects.first()
        status2del = InvoiceStatus.objects.create(name='OK')

        invoice = self.create_invoice_n_orgas(user=user, name='Nerv')[0]
        invoice.status = status2del
        invoice.save()

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='invoice_status',
            new_status=new_status,
            doc=invoice,
        )

    def test_delete_payment_terms(self):
        user = self.login_as_root_and_get()

        self.assertGET200(
            reverse('creme_config__model_portal', args=('billing', 'payment_terms')),
        )

        pterms = PaymentTerms.objects.create(name='3 months')

        invoice = self.create_invoice_n_orgas(user=user, name='Nerv')[0]
        invoice.payment_terms = pterms
        invoice.save()

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('billing', 'payment_terms', pterms.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(PaymentTerms).job
        job.type.execute(job)
        self.assertDoesNotExist(pterms)

        invoice = self.assertStillExists(invoice)
        self.assertIsNone(invoice.payment_terms)

    def test_delete_currency(self):
        user = self.login_as_root_and_get()

        currency = Currency.objects.create(
            name='Berry', local_symbol='B', international_symbol='BRY',
        )
        invoice = self.create_invoice_n_orgas(user=user, name='Nerv', currency=currency)[0]

        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'currency', currency.id),
        ))
        self.assertFormError(
            self.get_form_or_fail(response),
            field='replace_billing__invoice_currency',
            errors=_('Deletion is not possible.'),
        )

        invoice = self.assertStillExists(invoice)
        self.assertEqual(currency, invoice.currency)

    def test_delete_additional_info(self):
        user = self.login_as_root_and_get()

        info = AdditionalInformation.objects.create(name='Agreement')
        invoice = self.create_invoice_n_orgas(user=user, name='Nerv')[0]
        invoice.additional_info = info
        invoice.save()

        response = self.client.post(reverse(
            'creme_config__delete_instance',
            args=('billing', 'additional_information', info.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(AdditionalInformation).job
        job.type.execute(job)
        self.assertDoesNotExist(info)

        invoice = self.assertStillExists(invoice)
        self.assertIsNone(invoice.additional_info)


@skipIfCustomOrganisation
@skipIfCustomInvoice
@skipIfCustomProductLine
@skipIfCustomServiceLine
class InvoiceDeletionTestCase(_BillingTestCaseMixin, CremeTransactionTestCase):
    def setUp(self):  # setUpClass does not work here
        super().setUp()
        self.populate('creme_core', 'creme_config', 'billing')
        self.user = self.login_as_root_and_get()

        # NB: we need pk=1 for the default instances created by formset for detail-view.
        #     It would not be useful if we reset ID sequences...
        Vat.objects.get_or_create(id=1, value=Decimal('0.0'))

    def test_delete(self):
        user = self.user
        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Invoice001')
        product_line = ProductLine.objects.create(
            user=user,
            related_document=invoice,
            on_the_fly_item='My product',
        )
        service_line = ServiceLine.objects.create(
            user=user,
            related_document=invoice,
            on_the_fly_item='My service',
        )

        b_addr = invoice.billing_address
        self.assertIsInstance(b_addr, Address)

        s_addr = invoice.billing_address
        self.assertIsInstance(s_addr, Address)

        self.refresh(invoice).delete()
        self.assertDoesNotExist(invoice)
        self.assertDoesNotExist(product_line)
        self.assertDoesNotExist(service_line)

        self.assertStillExists(source)
        self.assertStillExists(target)

        self.assertDoesNotExist(b_addr)
        self.assertDoesNotExist(s_addr)

    def test_delete__protected(self):
        "Cannot be deleted."
        user = self.user
        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Invoice001')
        service_line = ServiceLine.objects.create(
            user=user, related_document=invoice, on_the_fly_item='Flyyyyy',
        )
        rel1 = Relation.objects.get(
            subject_entity=invoice.id, object_entity=service_line.id,
        )

        # This relation prohibits the deletion of the invoice
        ce = CremeEntity.objects.create(user=user)
        rtype = RelationType.objects.builder(
            id='test-subject_linked', predicate='is linked to',
            is_internal=True,
        ).symmetric(id='test-object_linked', predicate='is linked to').get_or_create()[0]
        rel2 = Relation.objects.create(
            subject_entity=invoice, object_entity=ce, type=rtype, user=user,
        )

        self.assertRaises(ProtectedError, self.refresh(invoice).delete)

        try:
            Invoice.objects.get(pk=invoice.pk)
            Organisation.objects.get(pk=source.pk)
            Organisation.objects.get(pk=target.pk)

            CremeEntity.objects.get(pk=ce.id)
            Relation.objects.get(pk=rel2.id)

            ServiceLine.objects.get(pk=service_line.pk)
            Relation.objects.get(pk=rel1.id)
        except Exception as e:
            self.fail(
                f'Exception: ({e}). Maybe the db does not support transaction?'
            )  # pragma: no cover
