from decimal import Decimal
from functools import partial
from json import dumps as json_dump
from unittest.mock import patch

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext as _
from parameterized import parameterized

from creme.billing import bricks
from creme.creme_core.models import FakeOrganisation, Vat  # Relation
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.models import Contact, Organisation
from creme.persons.tests.base import skipIfCustomOrganisation
from creme.products.models import Product, Service, SubCategory
from creme.products.tests.base import skipIfCustomProduct, skipIfCustomService

from ..constants import REL_SUB_HAS_LINE, REL_SUB_LINE_RELATED_ITEM
from .base import (
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
class LineTestCase(BrickTestCaseMixin, _BillingTestCase):
    @staticmethod
    def _build_msave_url(bdocument):
        return reverse('billing__multi_save_lines', args=(bdocument.id,))

    def test_clean01(self):
        "Discount.PERCENT."
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

    def test_clean02(self):
        "Discount.LINE_AMOUNT."
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

    def test_clean03(self):
        "Discount.ITEM_AMOUNT."
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

    def test_clean04(self):
        "With related item."
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

    def test_clean05(self):
        "On-the-fly item."
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
    def test_add_product_lines(self):
        "Multiple adding."
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(name='Invoice001', user=self.create_user())[0]
        url = reverse('billing__create_product_lines', args=(invoice.id,))
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add-popup.html')

        context = response1.context
        self.assertEqual(
            _('Add one or more product to «{entity}»').format(entity=invoice),
            context.get('title'),
        )
        self.assertEqual(_('Save the lines'), context.get('submit_label'))

        # ---
        self.assertFalse(invoice.get_lines(ServiceLine))

        product1 = self.create_product(user=user)
        product2 = self.create_product(user=user)
        vat = Vat.objects.get_or_create(value=Decimal('5.5'))[0]
        quantity = 2
        self.assertNoFormError(self.client.post(
            url,
            data={
                'items': self.formfield_value_multi_creator_entity(product1, product2),
                'quantity':       quantity,
                'discount_value': Decimal('20'),
                'vat':            vat.id,
            },
        ))

        invoice = self.refresh(invoice)  # Refresh lines cache
        lines = invoice.get_lines(ProductLine)
        self.assertEqual(2, len(lines))

        line0, line1 = lines
        self.assertEqual(quantity, line0.quantity)
        self.assertEqual(quantity, line1.quantity)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_HAS_LINE,          object=line0)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_HAS_LINE,          object=line1)
        self.assertHaveRelation(subject=line0,   type=REL_SUB_LINE_RELATED_ITEM, object=product1)
        self.assertHaveRelation(subject=line1,   type=REL_SUB_LINE_RELATED_ITEM, object=product2)

        self.assertEqual(Decimal('3.2'),  invoice.total_no_vat)  # 2 * 0.8 + 2 * 0.8
        self.assertEqual(Decimal('3.38'), invoice.total_vat)  # 3.2 * 1.07 = 3.38

        self.assertEqual(Product, line0.related_item_class())

        # ---
        detail_url = invoice.get_absolute_url()
        self.assertEqual(detail_url, line0.get_absolute_url())

        response3 = self.assertGET200(detail_url)
        brick_node = self.get_brick_node(
            self.get_html_tree(response3.content),
            brick=bricks.ProductLinesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2, title='{count} Product', plural_title='{count} Products',
        )

    def test_addlines_not_superuser(self):
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice],
        )
        self.add_credentials(user.role, all='*')

        invoice = self.create_invoice_n_orgas(name='Invoice001', user=self.get_root_user())[0]
        self.assertGET200(reverse('billing__create_product_lines', args=(invoice.id,)))
        self.assertGET200(reverse('billing__create_service_lines', args=(invoice.id,)))

    def test_add_lines_link(self):
        "LINK creds are needed."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice],
        )
        self.add_credentials(user.role, all='!LINK')
        self.add_credentials(user.role, all='*', model=Organisation)

        invoice = self.create_invoice_n_orgas(name='Invoice001', user=self.get_root_user())[0]
        self.assertGET403(reverse('billing__create_product_lines', args=(invoice.id,)))
        self.assertGET403(reverse('billing__create_service_lines', args=(invoice.id,)))

    def test_addlines_bad_related(self):
        "Related is not a billing entity."
        user = self.login_as_root_and_get()

        orga = Organisation.objects.create(user=user, name='Acme')
        self.assertGET404(reverse('billing__create_product_lines', args=(orga.id,)))
        self.assertGET404(reverse('billing__create_service_lines', args=(orga.id,)))

    @skipIfCustomProduct
    def test_lines_with_negatives_values(self):
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
    @skipIfCustomServiceLine
    def test_listviews(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)

        invoice1 = self.create_invoice(user=user, source=source, target=target, name='Invoice01')
        invoice2 = self.create_invoice(user=user, source=source, target=target, name='Invoice02')

        create_pline = partial(ProductLine.objects.create, user=user)
        pline1 = create_pline(related_document=invoice1, on_the_fly_item='FlyP1')
        pline2 = create_pline(related_document=invoice2, on_the_fly_item='FlyP2')

        create_sline = partial(ServiceLine.objects.create, user=user)
        sline1 = create_sline(related_document=invoice1, on_the_fly_item='FlyS1')
        sline2 = create_sline(related_document=invoice2, on_the_fly_item='FlyS2')

        # ---------------------------------------------------------------------
        product_response = self.assertGET200(reverse('billing__list_product_lines'))

        with self.assertNoException():
            plines_page = product_response.context['page_obj']

        self.assertEqual(2, plines_page.paginator.count)

        self.assertIn(pline1, plines_page.object_list)
        self.assertIn(pline2, plines_page.object_list)

        # ---------------------------------------------------------------------
        service_response = self.assertGET200(reverse('billing__list_service_lines'))

        with self.assertNoException():
            slines_page = service_response.context['page_obj']

        self.assertEqual(2, slines_page.paginator.count)

        self.assertIn(sline1, slines_page.object_list)
        self.assertIn(sline2, slines_page.object_list)

    @skipIfCustomProduct
    @skipIfCustomProductLine
    def test_listviews__related_to_deleted(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)

        product1 = self.create_product(user=user, name='Product #1')
        product2 = self.create_product(user=user, name='Deleted Product')
        product2.trash()

        create_invoice = partial(
            self.create_invoice, user=user, source=source, target=target,
        )
        invoice1 = create_invoice(name='Invoice01')
        invoice2 = create_invoice(name='Invoice02')
        invoice3 = create_invoice(name='Invoice03')
        invoice3.trash()

        create_pline = partial(ProductLine.objects.create, user=user)
        pline11 = create_pline(related_document=invoice1, on_the_fly_item='FlyP1')
        pline12 = create_pline(related_document=invoice1, related_item=product1)
        pline13 = create_pline(related_document=invoice1, related_item=product2)
        pline21 = create_pline(related_document=invoice2, on_the_fly_item='FlyP2')
        pline31 = create_pline(related_document=invoice3, related_item=product1)

        response = self.assertGET200(reverse('billing__list_product_lines'))

        with self.assertNoException():
            plines_page = response.context['page_obj']

        self.assertEqual(4, plines_page.paginator.count)

        lines = plines_page.object_list
        self.assertIn(pline11, lines)
        self.assertIn(pline12, lines)
        self.assertIn(pline13, lines)
        self.assertIn(pline21, lines)
        self.assertNotIn(pline31, lines)

    @skipIfCustomProductLine
    def test_delete_product_line01(self):
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

    @skipIfCustomService
    def test_add_service_lines01(self):
        "Multiple adding."
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(name='Invoice001', user=self.create_user())[0]
        url = reverse('billing__create_service_lines', args=(invoice.id,))
        self.assertGET200(url)
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'creme_core/generics/blockform/add-popup.html')

        context = response1.context
        self.assertEqual(
            _('Add one or more service to «{entity}»').format(entity=invoice),
            context.get('title'),
        )
        self.assertEqual(_('Save the lines'), context.get('submit_label'))

        # ---
        with self.assertRaises(AssertionError):
            invoice.get_lines(Service)

        service1 = self.create_service(user=user)
        service2 = self.create_service(user=user)
        vat = Vat.objects.get_or_create(value=Decimal('19.6'))[0]
        quantity = 2
        self.assertNoFormError(self.client.post(
            url,
            data={
                'items': self.formfield_value_multi_creator_entity(service1, service2),
                'quantity':       quantity,
                'discount_value': Decimal('10'),
                'vat':            vat.id,
            },
        ))

        invoice = self.refresh(invoice)  # Refresh lines cache
        lines = invoice.get_lines(ServiceLine)
        self.assertEqual(2, len(lines))

        line0 = lines[0]
        line1 = lines[1]
        self.assertEqual(quantity, line0.quantity)
        self.assertEqual(quantity, line1.quantity)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_HAS_LINE,          object=line0)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_HAS_LINE,          object=line1)
        self.assertHaveRelation(subject=line0,   type=REL_SUB_LINE_RELATED_ITEM, object=service1)
        self.assertHaveRelation(subject=line1,   type=REL_SUB_LINE_RELATED_ITEM, object=service2)

        self.assertEqual(Decimal('21.6'),  invoice.total_no_vat)  # 2 * 5.4 + 2 * 5.4
        self.assertEqual(Decimal('25.84'), invoice.total_vat)  # 21.6 * 1.196 = 25.84

        self.assertEqual(Service, line0.related_item_class())

        # ---
        detail_url = invoice.get_absolute_url()
        self.assertEqual(detail_url, line0.get_absolute_url())

        response3 = self.assertGET200(detail_url)
        brick_node = self.get_brick_node(
            self.get_html_tree(response3.content),
            brick=bricks.ServiceLinesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node,
            count=2, title='{count} Service', plural_title='{count} Services',
        )

    @skipIfCustomProductLine
    def test_related_document01(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]

        product_line = ProductLine.objects.create(
            user=user, related_document=invoice, on_the_fly_item='Flyyyyy',
        )
        self.assertEqual(invoice, product_line.related_document)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_HAS_LINE, object=product_line)

    @skipIfCustomProduct
    @skipIfCustomProductLine
    def test_related_item01(self):
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
    def test_related_item02(self):
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
    def test_related_item03(self):
        # Fill caches
        Vat.objects.default()
        ContentType.objects.get_for_model(ProductLine)

        with self.assertNumQueries(0):
            product_line = ProductLine()
            product = product_line.related_item

        self.assertIsNone(product)

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

    @skipIfCustomProductLine
    def test_multiple_delete01(self):
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
    def test_multiple_delete02(self):
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

    def test_delete_vat01(self):
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
    def test_delete_vat02(self):
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
    @skipIfCustomServiceLine
    def test_mass_import(self):
        self.login_as_root()
        self.assertGET404(self._build_import_url(ServiceLine))
        self.assertGET404(self._build_import_url(ProductLine))

    @staticmethod
    def _build_add2catalog_url(line):
        return reverse('billing__add_to_catalog', args=(line.id,))

    def test_convert_on_the_fly_line_to_real_item_error(self):
        "Entity is not a line."
        user = self.login_as_root_and_get()
        self.assertGET404(self._build_add2catalog_url(user.linked_contact))

    @skipIfCustomProductLine
    def test_convert_on_the_fly_line_to_real_item01(self):
        "Convert on the fly product."
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        unit_price = Decimal('50.0')
        product_name = 'on the fly product'
        product_line = ProductLine.objects.create(
            user=user, related_document=invoice,
            on_the_fly_item=product_name, unit_price=unit_price, unit='',
        )
        cat, subcat = self.create_cat_n_subcat()

        url = self._build_add2catalog_url(product_line)
        response = self.assertGET200(url)
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        self.assertEqual(
            _('Add this on the fly item to your catalog'),
            context.get('title'),
        )
        self.assertEqual(_('Add to the catalog'), context.get('submit_label'))

        enum_choiceset = self.get_form_or_fail(response).fields['sub_category'].enum
        self.assertEqual(enum_choiceset.field.model, Product)

        # ---
        response = self.client.post(url, data={"sub_category": subcat.pk})
        self.assertNoFormError(response)
        self.assertTrue(Product.objects.exists())

        self.get_object_or_fail(
            Product,
            name=product_name,
            unit_price=unit_price,
            user=user,
            category=cat,
            sub_category=subcat,
        )

    @skipIfCustomServiceLine
    def test_convert_on_the_fly_line_to_real_item02(self):
        "Convert on the fly service."
        user = self.login_as_root_and_get()

        invoice  = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        unit_price = Decimal('50.0')
        service_name = 'on the fly service'
        service_line = ServiceLine.objects.create(
            user=user, related_document=invoice,
            on_the_fly_item=service_name, unit_price=unit_price, unit='',
        )
        cat, subcat = self.create_cat_n_subcat()

        url = self._build_add2catalog_url(service_line)
        response = self.assertGET200(url)

        enum_choiceset = self.get_form_or_fail(response).fields['sub_category'].enum
        self.assertEqual(enum_choiceset.field.model, Service)

        # Submit new service
        response = self.client.post(
            self._build_add2catalog_url(service_line),
            data={"sub_category": subcat.pk},
        )
        self.assertNoFormError(response)
        self.assertTrue(Service.objects.exists())

        self.get_object_or_fail(
            Service,
            name=service_name,
            unit_price=unit_price,
            user=user,
            category=cat,
            sub_category=subcat,
        )

    @skipIfCustomProductLine
    def test_convert_on_the_fly_line_to_real_item03(self):
        "On-the-fly + product creation + no creation creds."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Contact, Organisation],  # Not 'Product'
        )
        self.add_credentials(user.role, own='*')

        invoice  = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        product_line = ProductLine.objects.create(
            user=user, related_document=invoice,
            on_the_fly_item='on the fly service', unit_price=Decimal('50.0')
        )
        subcat = self.create_cat_n_subcat()[1]
        self.assertPOST403(
            self._build_add2catalog_url(product_line),
            data={"sub_category": subcat.pk},
        )

        self.assertFalse(Product.objects.exists())

    @skipIfCustomServiceLine
    def test_convert_on_the_fly_line_to_real_item04(self):
        "On-the-fly + service creation + no creation creds."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Contact, Organisation],  # Not 'Service'
        )
        self.add_credentials(user.role, own='*')

        invoice  = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        service_line = ServiceLine.objects.create(
            user=user, related_document=invoice,
            on_the_fly_item='on the fly service', unit_price=Decimal('50.0'),
        )
        subcat = self.create_cat_n_subcat()[1]
        self.assertPOST403(
            self._build_add2catalog_url(service_line),
            data={"sub_category": subcat.pk},
        )

        self.assertFalse(Service.objects.exists())

    @skipIfCustomProductLine
    def test_convert_on_the_fly_line_to_real_item05(self):
        "Already related item product line."
        user = self.login_as_root_and_get()

        product = self.create_product(user=user)
        invoice  = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        product_line = ProductLine.objects.create(
            user=user, related_document=invoice,
            related_item=product, unit_price=Decimal('50.0')
        )
        subcat = self.create_cat_n_subcat()[1]
        response = self.assertPOST200(
            self._build_add2catalog_url(product_line),
            data={"sub_category": subcat.pk},
        )

        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_(
                'You are not allowed to add this item to the catalog '
                'because it is not on the fly'
            ),
        )
        self.assertEqual(1, Product.objects.count())

    @skipIfCustomServiceLine
    def test_convert_on_the_fly_line_to_real_item06(self):
        "Already related item service line."
        user = self.login_as_root_and_get()

        service = self.create_service(user=user)
        invoice  = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        service_line = ServiceLine.objects.create(
            user=user, related_document=invoice,
            related_item=service, unit_price=Decimal('50.0'),
        )
        subcat = self.create_cat_n_subcat()[1]
        response = self.assertPOST200(
            self._build_add2catalog_url(service_line),
            data={"sub_category": subcat.pk},
        )

        self.assertFormError(
            self.get_form_or_fail(response),
            field=None,
            errors=_(
                'You are not allowed to add this item to the catalog '
                'because it is not on the fly'
            ),
        )
        self.assertEqual(1, Service.objects.count())

    @skipIfCustomServiceLine
    def test_multi_save_lines__1_edition(self):
        "1 service line updated."
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        service_line = ServiceLine.objects.create(
            user=user, related_document=invoice,
            on_the_fly_item='on the fly service', unit_price=Decimal('50.0'),
        )

        url = self._build_msave_url(invoice)
        self.assertGET405(url)

        name = 'on the fly service updated'
        unit_price = '100.0'
        quantity = '2'
        unit = 'day'
        discount = '20'
        discount_unit = ServiceLine.Discount.PERCENT
        response = self.client.post(
            url,
            data={
                service_line.entity_type_id: json_dump({
                    'service_line_formset-TOTAL_FORMS':       1,
                    'service_line_formset-INITIAL_FORMS':     1,
                    'service_line_formset-MAX_NUM_FORMS':     '',
                    'service_line_formset-0-cremeentity_ptr': service_line.id,
                    'service_line_formset-0-user':            user.id,
                    'service_line_formset-0-on_the_fly_item': name,
                    'service_line_formset-0-unit_price':      unit_price,
                    'service_line_formset-0-quantity':        quantity,
                    'service_line_formset-0-discount':        discount,
                    'service_line_formset-0-discount_unit':   discount_unit,
                    'service_line_formset-0-vat_value':       Vat.objects.all()[1].id,
                    'service_line_formset-0-unit':            unit,
                }),
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(1, ServiceLine.objects.count())

        service_line = self.refresh(service_line)
        self.assertEqual(name,                service_line.on_the_fly_item)
        self.assertEqual(Decimal(unit_price), service_line.unit_price)
        self.assertEqual(Decimal(quantity),   service_line.quantity)
        self.assertEqual(unit,                service_line.unit)
        self.assertEqual(Decimal(discount),   service_line.discount)
        self.assertEqual(discount_unit,       service_line.discount_unit)

    @skipIfCustomProductLine
    def test_multi_save_lines__1_creation_1_deletion(self):
        "1 product line created on the fly and 1 deleted."
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        product_line = ProductLine.objects.create(
            user=user, related_document=invoice,
            on_the_fly_item='on the fly service', unit_price=Decimal('50.0'),
        )
        name = 'new on the fly product'
        unit_price = '69.0'
        quantity = '2'
        unit = 'month'
        response = self.client.post(
            self._build_msave_url(invoice),
            data={
                product_line.entity_type_id: json_dump({
                    'product_line_formset-TOTAL_FORMS':       2,
                    'product_line_formset-INITIAL_FORMS':     1,
                    'product_line_formset-MAX_NUM_FORMS':     '',
                    'product_line_formset-0-DELETE':          True,
                    'product_line_formset-0-cremeentity_ptr': product_line.id,
                    'product_line_formset-0-user':            user.id,
                    'product_line_formset-0-on_the_fly_item': 'whatever',
                    'product_line_formset-0-unit_price':      'whatever',
                    'product_line_formset-0-quantity':        'whatever',
                    'product_line_formset-0-discount':        'whatever',
                    'product_line_formset-0-discount_unit':   'whatever',
                    'product_line_formset-0-vat_value':       'whatever',
                    'product_line_formset-0-unit':            'whatever',
                    'product_line_formset-1-user':            user.id,
                    'product_line_formset-1-on_the_fly_item': name,
                    'product_line_formset-1-unit_price':      unit_price,
                    'product_line_formset-1-quantity':        quantity,
                    'product_line_formset-1-discount':        '50.00',
                    'product_line_formset-1-discount_unit':   '1',
                    'product_line_formset-1-vat_value':       Vat.objects.all()[0].id,
                    'product_line_formset-1-unit':            unit,
                }),
            },
        )
        self.assertNoFormError(response)

        product_line = self.get_alone_element(ProductLine.objects.all())
        self.assertEqual(name,                product_line.on_the_fly_item)
        self.assertEqual(Decimal(unit_price), product_line.unit_price)
        self.assertEqual(Decimal(quantity),   product_line.quantity)
        self.assertEqual(unit,                product_line.unit)
        self.assertEqual(1,                   product_line.order)

    @skipIfCustomServiceLine
    def test_multi_save_lines__credentials_error(self):
        "No CHANGE creds."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Contact, Organisation],
        )
        self.add_credentials(user.role, all='!CHANGE')

        invoice  = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        service_line = ServiceLine.objects.create(
            user=user, related_document=invoice,
            on_the_fly_item='on the fly service', unit_price=Decimal('50.0'),
        )

        response = self.client.post(
            self._build_msave_url(invoice),
            data={
                service_line.entity_type_id: json_dump({
                    'service_line_formset-TOTAL_FORMS':       1,
                    'service_line_formset-INITIAL_FORMS':     1,
                    'service_line_formset-MAX_NUM_FORMS':     '',
                    'service_line_formset-0-cremeentity_ptr': service_line.id,
                    'service_line_formset-0-user':            user.id,
                    'service_line_formset-0-on_the_fly_item': 'on the fly service updated',
                    'service_line_formset-0-unit_price':      '100.0',
                    'service_line_formset-0-quantity':        '2',
                    'service_line_formset-0-discount':        '20',
                    'service_line_formset-0-discount_unit':   '1',
                    'service_line_formset-0-vat_value':       Vat.objects.all()[0].id,
                    'service_line_formset-0-unit':            'day',
                }),
            },
        )
        self.assertContains(
            response,
            _('You are not allowed to edit this entity: {}').format(invoice),
            status_code=403,
            html=True,
        )

    @skipIfCustomServiceLine
    def test_multi_save_lines__discount_amount_per_line(self):
        "Other type of discount: amount per line."
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        service_line = ServiceLine.objects.create(
            user=user, related_document=invoice,
            on_the_fly_item='on the fly service', unit_price=Decimal('50.0'),
        )

        discount_unit = ServiceLine.Discount.LINE_AMOUNT
        response = self.client.post(
            self._build_msave_url(invoice),
            data={
                service_line.entity_type_id: json_dump({
                    'service_line_formset-TOTAL_FORMS':       1,
                    'service_line_formset-INITIAL_FORMS':     1,
                    'service_line_formset-MAX_NUM_FORMS':     '',
                    'service_line_formset-0-cremeentity_ptr': service_line.id,
                    'service_line_formset-0-user':            user.id,
                    'service_line_formset-0-on_the_fly_item': 'on the fly service updated',
                    'service_line_formset-0-unit_price':      '100.0',
                    'service_line_formset-0-quantity':        '2',
                    'service_line_formset-0-discount':        '20',
                    'service_line_formset-0-discount_unit':   discount_unit,
                    'service_line_formset-0-vat_value':       Vat.objects.all()[1].id,
                    'service_line_formset-0-unit':            'day',
                }),
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(1, ServiceLine.objects.count())

        service_line = self.refresh(service_line)
        self.assertEqual(discount_unit, service_line.discount_unit)

    @skipIfCustomServiceLine
    def test_multi_save_lines__discount_amount_per_item(self):
        "Other type of discount: amount per item."
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        service_line = ServiceLine.objects.create(
            user=user, related_document=invoice,
            on_the_fly_item='on the fly service', unit_price=Decimal('50.0'),
        )

        discount_unit = ServiceLine.Discount.ITEM_AMOUNT
        response = self.client.post(
            self._build_msave_url(invoice),
            data={
                service_line.entity_type_id: json_dump({
                    'service_line_formset-TOTAL_FORMS':       1,
                    'service_line_formset-INITIAL_FORMS':     1,
                    'service_line_formset-MAX_NUM_FORMS':     '',
                    'service_line_formset-0-cremeentity_ptr': service_line.id,
                    'service_line_formset-0-user':            user.id,
                    'service_line_formset-0-on_the_fly_item': 'on the fly service updated',
                    'service_line_formset-0-unit_price':      '100.0',
                    'service_line_formset-0-quantity':        '2',
                    'service_line_formset-0-discount':        '20',
                    'service_line_formset-0-discount_unit':   discount_unit,
                    'service_line_formset-0-vat_value':       Vat.objects.all()[1].id,
                    'service_line_formset-0-unit':            'day',
                }),
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(1, ServiceLine.objects.count())

        self.assertEqual(discount_unit, self.refresh(service_line).discount_unit)

    @skipIfCustomServiceLine
    def test_multi_save_lines__related_service(self):
        "1 service line updated with concrete related Service."
        user = self.login_as_root_and_get()

        sub_cat = SubCategory.objects.all()[0]
        shipping = Service.objects.create(
            user=user, name='Shipping',
            category=sub_cat.category,
            sub_category=sub_cat,
            unit_price=Decimal('60.0'),
        )

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        line = ServiceLine.objects.create(
            user=user, related_document=invoice,
            related_item=shipping,
            unit_price=Decimal('50.0'),
            vat_value=Vat.objects.all()[0],
        )

        response = self.client.post(
            self._build_msave_url(invoice),
            data={
                line.entity_type_id: json_dump({
                    'service_line_formset-TOTAL_FORMS':       1,
                    'service_line_formset-INITIAL_FORMS':     1,
                    'service_line_formset-MAX_NUM_FORMS':     '',
                    'service_line_formset-0-cremeentity_ptr': line.id,
                    'service_line_formset-0-user':            user.id,
                    # 'service_line_formset-0-on_the_fly_item': '',  # <==
                    'service_line_formset-0-unit_price':      '51',
                    'service_line_formset-0-quantity':        str(line.quantity),
                    'service_line_formset-0-discount':        str(line.discount),
                    'service_line_formset-0-discount_unit':   str(line.discount_unit),
                    'service_line_formset-0-vat_value':       line.vat_value_id,
                    'service_line_formset-0-unit':            line.unit,
                }),
            },
        )
        self.assertNoFormError(response)

        line = self.refresh(line)
        self.assertIsNone(line.on_the_fly_item)
        self.assertEqual(Decimal('51'), line.unit_price)

    def test_multi_save_lines__errors(self):
        "Bad related model."
        user = self.login_as_root_and_get()
        orga = FakeOrganisation.objects.create(user=user, name='Foxhound')
        ct_id = ContentType.objects.get_for_model(ProductLine).id
        self.assertPOST404(
            self._build_msave_url(orga),
            data={
                ct_id: json_dump({
                    'product_line_formset-TOTAL_FORMS':       1,
                    'product_line_formset-INITIAL_FORMS':     0,
                    'product_line_formset-MAX_NUM_FORMS':     '',
                    'product_line_formset-0-user':            user.id,
                    'product_line_formset-0-on_the_fly_item': 'New on the fly product',
                    'product_line_formset-0-unit_price':      '69.0',
                    'product_line_formset-0-quantity':        '2',
                    'product_line_formset-0-discount':        '50.00',
                    'product_line_formset-0-discount_unit':   '1',
                    'product_line_formset-0-vat_value':       Vat.objects.first().id,
                    'product_line_formset-0-unit':            'month',
                }),
            },
        )

    @skipIfCustomProductLine
    def test_multi_save_lines__validation_errors01(self):
        "No saved line."
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        name = 'new on the fly product'
        quantity = '2'
        unit = 'month'
        ct_id = ContentType.objects.get_for_model(ProductLine).id
        response = self.assertPOST409(
            self._build_msave_url(invoice),
            data={
                ct_id: json_dump({
                    'product_line_formset-TOTAL_FORMS':   1,
                    'product_line_formset-INITIAL_FORMS': 0,
                    'product_line_formset-MAX_NUM_FORMS':     '',
                    'product_line_formset-0-user':            user.id,
                    'product_line_formset-0-on_the_fly_item': name,
                    # 'product_line_formset-0-unit_price':    ...,   Missing
                    'product_line_formset-0-quantity':        quantity,
                    'product_line_formset-0-discount':        '50.00',
                    'product_line_formset-0-discount_unit':   '1',
                    'product_line_formset-0-vat_value':       Vat.objects.all()[0].id,
                    'product_line_formset-0-unit':            unit,
                }),
            },
        )
        self.assertTemplateUsed(response, 'billing/frags/lines-errors.html')

        errors = response.context.get('errors')
        self.assertIsList(errors, length=1)

        error = errors[0]
        self.assertIsDict(error, length=3)
        self.assertIsNone(error.get('item', -1))
        self.assertIn('instance', error)
        self.assertListEqual(
            [(ProductLine._meta.get_field('unit_price'), [_('This field is required.')])],
            error.get('errors'),
        )

    @skipIfCustomProductLine
    def test_multi_save_lines__validation_errors02(self):
        "Edited line + non field error."
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        line = ProductLine.objects.create(
            user=user, related_document=invoice,
            on_the_fly_item='Awesome product',
            unit_price=Decimal('50.0'),
            vat_value=Vat.objects.all()[0],
        )
        response = self.assertPOST409(
            self._build_msave_url(invoice),
            data={
                line.entity_type_id: json_dump({
                    'product_line_formset-TOTAL_FORMS':       1,
                    'product_line_formset-INITIAL_FORMS':     1,
                    'product_line_formset-MAX_NUM_FORMS':     '',
                    'product_line_formset-0-cremeentity_ptr': line.id,
                    'product_line_formset-0-user':            user.id,
                    'product_line_formset-0-on_the_fly_item': 'New name',
                    'product_line_formset-0-unit_price':      str(line.unit_price),
                    'product_line_formset-0-quantity':        str(line.quantity),
                    'product_line_formset-0-vat_value':       line.vat_value_id,
                    'product_line_formset-0-unit':            line.unit,

                    # Error:
                    'product_line_formset-0-discount_unit': str(ProductLine.Discount.PERCENT),
                    'product_line_formset-0-discount':      '101.00',
                }),
            },
        )
        self.assertTemplateUsed(response, 'billing/frags/lines-errors.html')

        errors = response.context.get('errors')
        self.assertIsList(errors, length=1)

        error = errors[0]
        self.assertIsDict(error, length=3)
        self.assertEqual(line.on_the_fly_item, error.get('item'))  # Not 'New name'
        self.assertIn('instance', error)
        self.assertListEqual(
            [(
                None,
                [_(
                    'If you choose % for your discount unit, '
                    'your discount must be between 1 and 100%'
                )],
            )],
            error.get('errors'),
        )

    @skipIfCustomProductLine
    def test_multiple_save_lines__order(self):
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        lines = [
            ProductLine.objects.create(
                user=user, related_document=invoice,
                unit_price=Decimal('50.0'), on_the_fly_item=f'Product {order}',
                order=order,
            ) for order in range(1, 4)
        ]

        data = {
            'product_line_formset-TOTAL_FORMS': len(lines) + 1,
            'product_line_formset-INITIAL_FORMS': len(lines),
            'product_line_formset-MAX_NUM_FORMS': '',
        }

        for index, line in enumerate(lines):
            data.update({
                f'product_line_formset-{index}-cremeentity_ptr': line.id,
                f'product_line_formset-{index}-user':            user.id,
                f'product_line_formset-{index}-on_the_fly_item': line.on_the_fly_item,
                f'product_line_formset-{index}-unit_price':      str(line.unit_price),
                f'product_line_formset-{index}-quantity':        str(line.quantity),
                f'product_line_formset-{index}-discount':        str(line.discount),
                f'product_line_formset-{index}-discount_unit':   str(line.discount_unit),
                f'product_line_formset-{index}-vat_value':       line.vat_value_id,
                f'product_line_formset-{index}-unit':            line.unit,
            })

        data.update({
            'product_line_formset-3-user':            user.id,
            'product_line_formset-3-on_the_fly_item': 'New on the fly product',
            'product_line_formset-3-unit_price':      '69.0',
            'product_line_formset-3-quantity':        '2',
            'product_line_formset-3-discount':        '50.00',
            'product_line_formset-3-discount_unit':   '1',
            'product_line_formset-3-vat_value':       Vat.objects.first().id,
            'product_line_formset-3-unit':            'month',
        })

        response = self.client.post(
            self._build_msave_url(invoice),
            data={lines[0].entity_type_id: json_dump(data)},
        )

        self.assertNoFormError(response)

        self.assertEqual([
            (1, 'Product 1'),
            (2, 'Product 2'),
            (3, 'Product 3'),
            (4, 'New on the fly product'),
        ], [
            (line.order, line.on_the_fly_item)
            for line in ProductLine.objects.order_by('order')
        ])

    @parameterized.expand([
        ('Product 1', 3, [
            (1, 'Product 2'),
            (2, 'Product 3'),
            (3, 'Product 1'),
            (0, 'Service 1'),
            (0, 'Service 2'),
        ]),
        ('Product 3', 1, [
            (1, 'Product 3'),
            (2, 'Product 1'),
            (3, 'Product 2'),
            (0, 'Service 1'),
            (0, 'Service 2'),
        ]),
        ('Product 1', 2, [
            (1, 'Product 2'),
            (2, 'Product 1'),
            (3, 'Product 3'),
            (0, 'Service 1'),
            (0, 'Service 2'),
        ]),
        ('Service 1', 3, [
            (0, 'Product 1'),
            (0, 'Product 2'),
            (0, 'Product 3'),
            (1, 'Service 2'),
            (2, 'Service 1'),
        ]),
    ])
    @skipIfCustomProductLine
    def test_reorder_lines(self, target_name, next_order, expected):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001', discount=0)[0]
        default_vat = Vat.objects.default()
        create_prod_line = partial(
            ProductLine.objects.create,
            user=user, related_document=invoice, vat_value=default_vat, unit_price=Decimal('10'),
        )
        create_serv_line = partial(
            ServiceLine.objects.create,
            user=user, related_document=invoice, vat_value=default_vat, unit_price=Decimal('10'),
        )

        lines = {
            **{
                f'Product {order}': create_prod_line(on_the_fly_item=f'Product {order}')
                for order in range(1, 4)
            },
            **{
                f'Service {order}': create_serv_line(on_the_fly_item=f'Service {order}')
                for order in range(1, 3)
            }
        }

        url = reverse('billing__reorder_line', args=(invoice.pk, lines[target_name].pk))

        with patch('creme.billing.models.Invoice.save') as fake_invoice_save:
            response = self.client.post(url, data={'target': next_order})
            self.assertEqual(response.status_code, 200)

        invoice.refresh_from_db()
        self.assertEqual(
            [
                (line.order, line.on_the_fly_item)
                for model in (ProductLine, ServiceLine)
                for line in invoice.get_lines(model).order_by('order')
            ],
            expected,
        )

        # billing document save() is never called !
        self.assertEqual(0, fake_invoice_save.call_count)

    def test_reorder_lines__invalid_ids(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001', discount=0)[0]

        line = ProductLine.objects.create(
            user=user, related_document=invoice, vat_value=Vat.objects.default(),
            unit_price=Decimal('10'), on_the_fly_item='Product A'
        )
        data = {'target': 1}

        self.assertPOST404(
            reverse('billing__reorder_line', args=(line.pk, line.pk)), data=data
        )
        self.assertPOST404(
            reverse('billing__reorder_line', args=(invoice.pk, invoice.pk)), data=data
        )
        self.assertPOST404(
            reverse('billing__reorder_line', args=(999999, line.pk)), data=data
        )
        self.assertPOST404(
            reverse('billing__reorder_line', args=(invoice.pk, 9999999)), data=data
        )

    def test_reorder_lines__invalid_perms(self):
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice, Organisation]
        )
        self.add_credentials(user.role, own='!CHANGE')

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001', discount=0)[0]
        self.assertFalse(user.has_perm_to_change(invoice))

        line = ProductLine.objects.create(
            user=user, related_document=invoice, vat_value=Vat.objects.default(),
            unit_price=Decimal('10'), on_the_fly_item='Product A'
        )

        self.assertPOST403(
            reverse('billing__reorder_line', args=(invoice.pk, line.pk)), data={'target': 1}
        )

    def test_reorder_lines__invalid_target(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001', discount=0)[0]

        line = ProductLine.objects.create(
            user=user, related_document=invoice, vat_value=Vat.objects.default(),
            unit_price=Decimal('10'), on_the_fly_item='Product A'
        )

        url = reverse('billing__reorder_line', args=(invoice.pk, line.pk))

        self.assertPOST404(url, data={})
        self.assertPOST409(url, data={'target': 0})

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
    def test_discount01(self):
        "No discount."
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
    def test_discount02(self):
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
    def test_discount03(self):
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
    def test_discount04(self):
        "DISCOUNT_ITEM_AMOUNT."
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
    def test_discount05(self):
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

    @skipIfCustomProductLine
    def test_inneredit(self):
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001', discount=0)[0]
        pline = ProductLine.objects.create(
            user=user, unit_price=Decimal('10'),
            vat_value=Vat.objects.default(),
            related_document=invoice,
            on_the_fly_item='Flyyyyy',
            comment='I believe',
        )

        build_uri = self.build_inneredit_uri
        field_name = 'comment'
        uri = build_uri(pline, field_name)
        self.assertGET200(uri)

        comment = pline.comment + ' I can flyyy'
        response = self.client.post(uri, data={field_name:  comment})
        self.assertNoFormError(response)
        self.assertEqual(comment, self.refresh(pline).comment)

        self.assertGET404(build_uri(pline, 'on_the_fly_item'))
