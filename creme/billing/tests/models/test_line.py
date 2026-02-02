from decimal import Decimal
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.billing.constants import REL_SUB_HAS_LINE, REL_SUB_LINE_RELATED_ITEM
from creme.creme_core.models import Vat
from creme.persons.models import Organisation
from creme.persons.tests.base import skipIfCustomOrganisation
from creme.products.tests.base import skipIfCustomProduct

from ..base import (
    Invoice,
    ProductLine,
    ServiceLine,
    _BillingTestCase,
    skipIfCustomInvoice,
    skipIfCustomProductLine,
    skipIfCustomServiceLine,
)


@skipIfCustomOrganisation
@skipIfCustomInvoice
class LineTestCase(_BillingTestCase):
    def test_clean__discount__percent(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice01', discount=0)[0]
        kwargs = {
            'user': user,
            'related_document': invoice,
            'on_the_fly_item': 'Flyyy product',
            'vat_value': Vat.objects.get_or_create(value=Decimal('0'))[0],
            'discount_unit': ProductLine.Discount.PERCENT,
        }

        with self.assertRaises(ValidationError):
            ProductLine(discount=Decimal('-1'), ** kwargs).clean()

        with self.assertRaises(ValidationError):
            ProductLine(discount=Decimal('101'), ** kwargs).clean()

        with self.assertNoException():
            ProductLine(discount=Decimal('50'), ** kwargs).clean()

    def test_clean__discount__line_amount(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice01', discount=0)[0]
        kwargs = {
            'user': user,
            'related_document': invoice,
            'vat_value': Vat.objects.get_or_create(value=Decimal('0'))[0],

            'on_the_fly_item': 'Flyyy product',
            'discount_unit': ProductLine.Discount.LINE_AMOUNT,
        }

        with self.assertRaises(ValidationError):
            ProductLine(
                discount=Decimal('101'),
                unit_price=Decimal('100.00'),
                quantity=1,
                ** kwargs
            ).clean()

        with self.assertRaises(ValidationError):
            ProductLine(
                discount=Decimal('81'),
                unit_price=Decimal('40.00'),
                quantity=2,
                ** kwargs
            ).clean()

        with self.assertNoException():
            ProductLine(
                discount=Decimal('99'),
                unit_price=Decimal('100.00'),
                quantity=1,
                **kwargs
            ).clean()

    def test_clean__discount__item_amount(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice01', discount=0)[0]
        kwargs = {
            'user': user,
            'related_document': invoice,
            'vat_value': Vat.objects.get_or_create(value=Decimal('0'))[0],

            'on_the_fly_item': 'Flyyy product',
            'discount_unit': ProductLine.Discount.ITEM_AMOUNT,
        }

        with self.assertRaises(ValidationError):
            ProductLine(
                discount=Decimal('101'),
                unit_price=Decimal('100.00'),
                quantity=1,
                ** kwargs
            ).clean()

        with self.assertRaises(ValidationError):
            ProductLine(
                discount=Decimal('41'),
                unit_price=Decimal('40.00'),
                quantity=2,
                ** kwargs
            ).clean()

        with self.assertNoException():
            ProductLine(
                discount=Decimal('99'),
                unit_price=Decimal('100.00'),
                quantity=1,
                **kwargs
            ).clean()

    def test_clean__related_item(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice01', discount=0)[0]
        product = self.create_product(user=user)
        kwargs = {
            'user': user,
            'related_document': invoice,
            'related_item': product,
        }

        with self.assertRaises(ValidationError) as cm:
            ProductLine(on_the_fly_item='Flyyy product', ** kwargs).clean()

        self.assertValidationError(
            cm.exception,
            messages=_('You cannot set an on the fly name to a line with a related item'),
            codes='useless_name',
        )

        with self.assertNoException():
            ProductLine(**kwargs).clean()

    def test_clean__on_the_fly_item(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice01', discount=0)[0]
        kwargs = {
            'user': user,
            'related_document': invoice,
        }

        with self.assertRaises(ValidationError) as cm:
            ProductLine(** kwargs).clean()

        self.assertValidationError(
            cm.exception,
            messages=_('You must define a name for an on the fly item'),
            codes='required_name',
        )

        with self.assertNoException():
            ProductLine(on_the_fly_item='Flyyy product', **kwargs).clean()

    @skipIfCustomProduct
    def test_negatives_values(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        quote = self.create_quote_n_orgas(user=user, name='Quote001')[0]
        unit_price = Decimal('-50.0')
        product_name = 'on the fly product'
        create_pline = partial(
            ProductLine.objects.create,
            user=user, on_the_fly_item=product_name,
            unit_price=unit_price, unit='',
            vat_value=self.get_object_or_fail(Vat, value='0.0'),
        )
        create_pline(related_document=quote)
        create_pline(related_document=invoice)
        self.assertEqual(Decimal('-50.0'), invoice.total_vat)
        self.assertEqual(Decimal('0'), quote.total_vat)

    @skipIfCustomProductLine
    def test_delete_product_line(self):
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        product_line = ProductLine.objects.create(
            user=user, related_document=invoice, on_the_fly_item='Flyyyyy',
        )
        self.assertPOST409(
            reverse(
                'creme_core__delete_related_to_entity',
                args=(product_line.entity_type_id,),
            ),
            data={'id': product_line.id},
        )
        self.assertPOST200(product_line.get_delete_absolute_url(), follow=True)
        self.assertFalse(self.refresh(invoice).get_lines(ProductLine))
        self.assertFalse(ProductLine.objects.exists())

    @skipIfCustomProduct
    @skipIfCustomProductLine
    def test_related_item(self):
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        product = self.create_product(user=user)

        product_line = ProductLine.objects.create(
            user=user, related_document=invoice, related_item=product,
        )
        self.assertEqual(product, product_line.related_item)
        self.assertHaveRelation(product_line, type=REL_SUB_LINE_RELATED_ITEM, object=product)

        product_line = self.refresh(product_line)
        with self.assertNumQueries(2):
            p = product_line.related_item

        self.assertEqual(product, p)

    @skipIfCustomProductLine
    def test_related_item__none(self):
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        product_line = ProductLine.objects.create(
            user=user, related_document=invoice, on_the_fly_item='Flyyyyy',
        )
        self.assertIsNone(product_line.related_item)

        product_line = self.refresh(product_line)
        with self.assertNumQueries(0):
            p = product_line.related_item

        self.assertIsNone(p)

    @skipIfCustomProductLine
    def test_related_item__not_saved(self):
        # Fill caches
        Vat.objects.default()
        ContentType.objects.get_for_model(ProductLine)

        with self.assertNumQueries(0):
            product_line = ProductLine()
            product = product_line.related_item

        self.assertIsNone(product)

    @skipIfCustomProductLine
    def test_related_document(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]

        product_line = ProductLine.objects.create(
            user=user, related_document=invoice, on_the_fly_item='Flyyyyy',
        )
        self.assertEqual(invoice, product_line.related_document)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_HAS_LINE, object=product_line)

    @skipIfCustomProductLine
    def test_multiple_delete(self):
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001', discount=0)[0]

        create_line = partial(
            ProductLine.objects.create,
            user=user, related_document=invoice,
            vat_value=self.get_object_or_fail(Vat, value='0.0'),
        )
        ids = tuple(
            create_line(on_the_fly_item=f'Fly {price}', unit_price=Decimal(price)).id
            for price in ('10', '20')
        )

        invoice.save()  # Updates totals

        self.assertEqual(2, len(invoice.get_lines(ProductLine)))
        expected_total = Decimal('30')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

        self.assertPOST200(
            reverse('creme_core__delete_entities'),
            follow=True, data={'ids': '{},{}'.format(*ids)},
        )
        self.assertFalse(ProductLine.objects.filter(pk__in=ids))

        invoice = self.refresh(invoice)
        self.assertFalse(invoice.get_lines(ProductLine))

        expected_total = Decimal('0')
        self.assertEqual(expected_total, invoice.total_no_vat)
        self.assertEqual(expected_total, invoice.total_vat)

    @skipIfCustomProductLine
    def test_multiple_delete__forbidden(self):
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Organisation]
        )
        self.add_credentials(user.role, own='!CHANGE')

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001', discount=0)[0]
        self.assertFalse(user.has_perm_to_change(invoice))

        create_line = partial(
            ProductLine.objects.create, user=user, related_document=invoice
        )
        ids = tuple(
            create_line(on_the_fly_item=f'Fly {price}', unit_price=Decimal(price)).id
            for price in ('10', '20')
        )

        self.assertPOST403(
            reverse('creme_core__delete_entities'),
            follow=True, data={'ids': '{},{}'.format(*ids)}
        )
        self.assertEqual(2, ProductLine.objects.filter(pk__in=ids).count())

    def test_delete_vat__not_used(self):
        self.login_as_root()

        vat = Vat.objects.create(value=Decimal('5.0'), is_default=True, is_custom=True)
        response = self.client.post(reverse(
            'creme_config__delete_instance', args=('creme_core', 'vat_value', vat.id),
        ))
        self.assertNoFormError(response)

        job = self.get_deletion_command_or_fail(Vat).job
        job.type.execute(job)
        self.assertDoesNotExist(vat)

    @skipIfCustomProductLine
    def test_delete_vat__used(self):
        user = self.login_as_root_and_get()

        vat = Vat.objects.create(value=Decimal('5.0'), is_default=True, is_custom=True)
        invoice = self.create_invoice_n_orgas(user=user, name='Nerv')[0]
        ProductLine.objects.create(
            user=user, related_document=invoice, on_the_fly_item='Flyyyyy', vat_value=vat,
        )

        response = self.assertPOST200(reverse(
            'creme_config__delete_instance', args=('creme_core', 'vat_value', vat.id)
        ))
        self.assertFormError(
            self.get_form_or_fail(response),
            field='replace_billing__productline_vat_value',
            errors=_('Deletion is not possible.'),
        )

    @skipIfCustomProductLine
    def test_global_discount_change(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001', discount=0)[0]

        ProductLine.objects.create(
            user=user, unit_price=Decimal('10'),
            vat_value=Vat.objects.default(),
            related_document=invoice,
            on_the_fly_item='Flyyyyy',
        )

        discount_zero = Decimal('0.0')
        full_discount = Decimal('100.0')

        self.assertEqual(invoice.discount, discount_zero)

        invoice.discount = full_discount
        invoice.save()

        invoice = self.refresh(invoice)

        self.assertEqual(invoice.discount, full_discount)
        self.assertEqual(invoice.total_no_vat, discount_zero)
        self.assertEqual(invoice.total_vat, discount_zero)

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_discount__no_discount(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]

        kwargs = {
            'user': user,
            'related_document': invoice,
            'vat_value': Vat.objects.get_or_create(value=Decimal('0'))[0],

            'discount': Decimal('0'),
            'discount_unit': ProductLine.Discount.PERCENT,

            'quantity': 2,
        }
        product_line = ProductLine.objects.create(
            on_the_fly_item='Flyyy product',
            unit_price=Decimal('100.00'),
            **kwargs
        )
        self.assertEqual(Decimal('200.00'), product_line.get_price_exclusive_of_tax())

        service_line = ServiceLine.objects.create(
            on_the_fly_item='Flyyy service',
            unit_price=Decimal('0.00'),
            **kwargs
        )
        self.assertEqual(Decimal('0'), service_line.get_price_exclusive_of_tax())

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_discount__percent(self):
        "Discount.PERCENT."
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]

        kwargs = {
            'user': user,
            'related_document': invoice,
            'vat_value': Vat.objects.get_or_create(value=Decimal('0'))[0],
        }
        product_line = ProductLine.objects.create(
            on_the_fly_item='Flyyy product',
            unit_price=Decimal('100.00'), quantity=2,
            discount=Decimal('10.00'), discount_unit=ProductLine.Discount.PERCENT,
            **kwargs
        )
        self.assertEqual(Decimal('180.00'), product_line.get_price_exclusive_of_tax())

        service_line = ServiceLine.objects.create(
            on_the_fly_item='Flyyy service',
            unit_price=Decimal('20.00'), quantity=3,
            discount=Decimal('3.00'), discount_unit=ServiceLine.Discount.PERCENT,
            **kwargs
        )
        self.assertEqual(Decimal('58.20'), service_line.get_price_exclusive_of_tax())

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_discount__line_amount(self):
        "Discount.LINE_AMOUNT."
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]

        kwargs = {
            'user': user,
            'related_document': invoice,
            'vat_value': Vat.objects.get_or_create(value=Decimal('0'))[0],
        }
        product_line = ProductLine.objects.create(
            on_the_fly_item='Flyyy product',
            unit_price=Decimal('100.00'), quantity=2,
            discount=Decimal('5.00'),
            discount_unit=ProductLine.Discount.LINE_AMOUNT,
            **kwargs
        )
        self.assertEqual(Decimal('195.00'), product_line.get_price_exclusive_of_tax())

        service_line = ServiceLine.objects.create(
            on_the_fly_item='Flyyy service',
            unit_price=Decimal('20.00'), quantity=3,
            discount=Decimal('3.00'),
            discount_unit=ServiceLine.Discount.LINE_AMOUNT,
            **kwargs
        )
        self.assertEqual(Decimal('57.00'), service_line.get_price_exclusive_of_tax())

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_discount__item_amount(self):
        "Discount.ITEM_AMOUNT."
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=0)[0]

        kwargs = {
            'user': user,
            'related_document': invoice,
            'vat_value': Vat.objects.get_or_create(value=Decimal('0'))[0],
        }
        product_line = ProductLine.objects.create(
            on_the_fly_item='Flyyy product',
            unit_price=Decimal('100.00'), quantity=2,
            discount=Decimal('5.00'),
            discount_unit=ProductLine.Discount.ITEM_AMOUNT,
            **kwargs
        )
        self.assertEqual(Decimal('190.00'), product_line.get_price_exclusive_of_tax())

        service_line = ServiceLine.objects.create(
            on_the_fly_item='Flyyy service',
            unit_price=Decimal('20.00'), quantity=3,
            discount=Decimal('3.00'),
            discount_unit=ServiceLine.Discount.ITEM_AMOUNT,
            **kwargs
        )
        self.assertEqual(Decimal('51.00'), service_line.get_price_exclusive_of_tax())

    @skipIfCustomProductLine
    def test_discount__document(self):
        "Document's discount."
        user = self.login_as_root_and_get()
        invoice1, source, target = self.create_invoice_n_orgas(
            user=user, name='Invoice01', discount=10,
        )

        kwargs = {
            'user': user,
            'unit_price': Decimal('100.00'),
            'quantity': 2,
            'vat_value': Vat.objects.get_or_create(value=Decimal('0'))[0],
            'discount': Decimal('0'),
            'discount_unit': ProductLine.Discount.PERCENT,
        }
        product_line1 = ProductLine.objects.create(
            related_document=invoice1,
            on_the_fly_item='Flyyy product 1',
            **kwargs
        )
        self.assertEqual(Decimal('180.00'), product_line1.get_price_exclusive_of_tax())

        invoice2 = self.create_invoice(
            name='Invoice02', user=user,
            source=source, target=target,
            discount=5,
            currency=invoice1.currency,
        )

        product_line2 = ProductLine.objects.create(
            related_document=invoice2,
            on_the_fly_item='Flyyy product 2',
            **kwargs
        )
        self.assertEqual(Decimal('190.00'), product_line2.get_price_exclusive_of_tax())

    @skipIfCustomProductLine
    def test_rounding_policy(self):
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001')[0]

        kwargs = {'user': user, 'related_document': invoice}
        product_line = ProductLine.objects.create(
            on_the_fly_item='Flyyy product',
            unit_price=Decimal('0.014'), quantity=1,
            **kwargs
        )
        # 0.014 rounded down to 0.01
        self.assertEqual(Decimal('0.01'), product_line.get_price_exclusive_of_tax())

        product_line = ProductLine.objects.create(
            on_the_fly_item='Flyyy product',
            unit_price=Decimal('0.015'), quantity=1,
            **kwargs
        )
        # 0.015 rounded up to 0.02
        self.assertEqual(Decimal('0.02'), product_line.get_price_exclusive_of_tax())

        product_line = ProductLine.objects.create(
            on_the_fly_item='Flyyy product',
            unit_price=Decimal('0.016'), quantity=1,
            **kwargs
        )
        # 0.016 rounded up to 0.02
        self.assertEqual(Decimal('0.02'), product_line.get_price_exclusive_of_tax())

    # @skipIfCustomProduct
    # @skipIfCustomProductLine
    # def test_product_line_clone__method(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #
    #     product = self.create_product(user=user)
    #     invoice1 = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
    #     invoice2 = self.create_invoice_n_orgas(user=user, name='Invoice002')[0]
    #
    #     product_line = ProductLine.objects.create(
    #         user=user, related_document=invoice1, related_item=product,
    #     )
    #     product_line2 = product_line.clone(invoice2)
    #
    #     product_line2 = self.refresh(product_line2)
    #     self.assertEqual(invoice2, product_line2.related_document)
    #     self.assertEqual(product, product_line2.related_item)
    #
    #     rel_filter = Relation.objects.filter
    #     self.assertListEqual(
    #         [product_line2.pk],
    #         [
    #             *rel_filter(
    #                 type=REL_SUB_HAS_LINE, subject_entity=invoice2,
    #             ).values_list('object_entity', flat=True),
    #         ],
    #     )
    #     self.assertCountEqual(
    #         [product_line.pk, product_line2.pk],
    #         rel_filter(
    #             type=REL_SUB_LINE_RELATED_ITEM, object_entity=product,
    #         ).values_list('subject_entity', flat=True),
    #     )
    #
    # @skipIfCustomServiceLine
    # def test_service_line_clone__method(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #
    #     service = self.create_service(user=user)
    #     invoice1 = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
    #     invoice2 = self.create_invoice_n_orgas(user=user, name='Invoice002')[0]
    #
    #     service_line1 = ServiceLine.objects.create(
    #         user=user, related_document=invoice1, related_item=service,
    #     )
    #
    #     service_line2 = service_line1.clone(invoice2)
    #     service_line2 = self.refresh(service_line2)
    #     self.assertEqual(invoice2, service_line2.related_document)
    #     self.assertEqual(service, service_line2.related_item)
    #     self.assertNotEqual(service_line1, service_line2)
    #
    #     rel_filter = Relation.objects.filter
    #     self.assertListEqual(
    #         [service_line1.pk],
    #         [
    #             *rel_filter(
    #                 type=REL_SUB_HAS_LINE, subject_entity=invoice1,
    #             ).values_list('object_entity', flat=True)
    #         ],
    #     )
    #     self.assertCountEqual(
    #         [service_line2.pk],
    #         rel_filter(
    #             type=REL_SUB_HAS_LINE, subject_entity=invoice2,
    #         ).values_list('object_entity', flat=True)
    #     )
    #     self.assertCountEqual(
    #         [service_line1.pk, service_line2.pk],
    #         rel_filter(
    #             type=REL_SUB_LINE_RELATED_ITEM, object_entity=service,
    #         ).values_list('subject_entity', flat=True)
    #     )
