from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template

from creme.billing.constants import UUID_ORDER_STATUS_ISSUED
from creme.billing.models import Line, NumberGeneratorItem, SalesOrderStatus
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import Vat
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

from ..base import (
    Address,
    ProductLine,
    SalesOrder,
    ServiceLine,
    _BillingTestCase,
    skipIfCustomSalesOrder,
    skipIfCustomServiceLine,
)


class SalesOrderStatusTestCase(_BillingTestCase):
    def test_create(self):
        statuses = [*SalesOrderStatus.objects.all()]
        self.assertEqual(4, len(statuses))

        default_status = self.get_alone_element(
            [status for status in statuses if status.is_default]
        )
        self.assertUUIDEqual(UUID_ORDER_STATUS_ISSUED, default_status.uuid)

        # New default status => previous default status is updated
        new_status1 = SalesOrderStatus.objects.create(name='OK', is_default=True)
        self.assertTrue(self.refresh(new_status1).is_default)
        self.assertEqual(5, SalesOrderStatus.objects.count())
        self.assertFalse(
            SalesOrderStatus.objects.exclude(id=new_status1.id).filter(is_default=True)
        )

        # No default status is found => new one is default one
        SalesOrderStatus.objects.update(is_default=False)
        new_status2 = SalesOrderStatus.objects.create(name='KO', is_default=False)
        self.assertTrue(self.refresh(new_status2).is_default)

    def test_render(self):
        user = self.get_root_user()
        status = SalesOrderStatus.objects.create(name='OK', color='00FF00')
        order = SalesOrder(user=user, name='OK Order', status=status)

        with self.assertNoException():
            render = Template(
                r'{% load creme_core_tags %}'
                r'{% print_field object=order field="status" tag=tag %}'
            ).render(Context({
                'user': user,
                'order': order,
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
@skipIfCustomSalesOrder
class SalesOrderTestCase(_BillingTestCase):
    def test_delete(self):
        user = self.login_as_root_and_get()
        order, source, target = self.create_salesorder_n_orgas(user=user, name='Nerv')

        kwargs = {
            'user': user, 'related_document': order,
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

        url = order.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            order = self.refresh(order)

        self.assertIs(order.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(order)
        self.assertDoesNotExist(product_line)
        self.assertDoesNotExist(service_line)
        self.assertStillExists(source)
        self.assertStillExists(target)

    def test_delete_status(self):
        user = self.login_as_root_and_get()
        new_status = SalesOrderStatus.objects.first()
        status2del = SalesOrderStatus.objects.create(name='OK')
        order = self.create_salesorder_n_orgas(user=user, name='Order', status=status2del)[0]
        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='sales_order_status',
            new_status=new_status,
            doc=order,
        )

    @skipIfCustomAddress
    @skipIfCustomServiceLine
    def test_clone__not_managed_emitter(self):
        "Organisation not managed => number is set to '0'."
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user=user)

        target.billing_address = Address.objects.create(
            name='Billing address 01',
            address='BA1 - Address', city='BA1 - City', zipcode='123',
            owner=target,
        )
        target.save()

        order = self.create_salesorder(
            user=user, name='Order #1', source=source, target=target,
            status=SalesOrderStatus.objects.exclude(is_default=True).first(),
        )
        sl = ServiceLine.objects.create(
            related_item=self.create_service(user=user), user=user, related_document=order,
            quantity=25, unit_price=100,
        )

        address_count = Address.objects.count()

        origin_b_addr = order.billing_address
        origin_b_addr.zipcode += ' (edited)'
        origin_b_addr.save()

        cloned = self.clone(order)
        self.assertIsInstance(cloned, SalesOrder)
        self.assertNotEqual(order.pk, cloned.pk)
        self.assertEqual(order.name,   cloned.name)
        self.assertEqual(order.status, cloned.status)
        self.assertEqual('',           cloned.number)

        self.assertEqual(source, cloned.source)
        self.assertEqual(target, cloned.target)

        # Lines are cloned
        cloned_line = self.get_alone_element(cloned.iter_all_lines())
        self.assertIsInstance(cloned_line, ServiceLine)
        self.assertNotEqual(sl.pk, cloned_line.pk)
        self.assertEqual(sl.related_item, cloned_line.related_item)
        self.assertEqual(sl.quantity,     cloned_line.quantity)
        self.assertEqual(sl.unit_price,   cloned_line.unit_price)

        # Addresses are cloned
        self.assertEqual(address_count + 2, Address.objects.count())

        billing_address = cloned.billing_address
        self.assertIsInstance(billing_address, Address)
        self.assertEqual(cloned,                billing_address.owner)
        self.assertEqual(origin_b_addr.name,    billing_address.name)
        self.assertEqual(origin_b_addr.city,    billing_address.city)
        self.assertEqual(origin_b_addr.zipcode, billing_address.zipcode)

    def test_clone__managed_emitter(self):
        "Organisation is managed => number is generated (but only once BUGFIX)."
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=source,
            numbered_type=ContentType.objects.get_for_model(SalesOrder),
        )
        item.data['format'] = 'ORD-{counter:04}'
        item.save()

        order = self.create_salesorder(user=user, name='My Order', source=source, target=target)
        self.assertEqual('ORD-0001', order.number)

        cloned = self.clone(order)
        self.assertEqual('ORD-0002', cloned.number)

    # @skipIfCustomAddress
    # @skipIfCustomServiceLine
    # def test_clone__method01(self):  # DEPRECATED
    #     "Organisation not managed => number is set to '0'."
    #     user = self.login_as_root_and_get()
    #     source, target = self.create_orgas(user=user)
    #
    #     target.billing_address = Address.objects.create(
    #         name='Billing address 01',
    #         address='BA1 - Address', city='BA1 - City', zipcode='123',
    #         owner=target,
    #     )
    #     target.save()
    #
    #     order = self.create_salesorder(
    #         user=user, name='Order #1', source=source, target=target,
    #         status=SalesOrderStatus.objects.exclude(is_default=True).first(),
    #     )
    #     sl = ServiceLine.objects.create(
    #         related_item=self.create_service(user=user), user=user, related_document=order,
    #         quantity=25, unit_price=100,
    #     )
    #
    #     address_count = Address.objects.count()
    #
    #     origin_b_addr = order.billing_address
    #     origin_b_addr.zipcode += ' (edited)'
    #     origin_b_addr.save()
    #
    #     cloned = order.clone()
    #     self.assertIsInstance(cloned, SalesOrder)
    #     self.assertNotEqual(order.pk, cloned.pk)
    #     self.assertEqual(order.name,   cloned.name)
    #     self.assertEqual(order.status, cloned.status)
    #     self.assertEqual('',           cloned.number)
    #
    #     self.assertEqual(source, cloned.source)
    #     self.assertEqual(target, cloned.target)
    #
    #     # Lines are cloned
    #     cloned_line = self.get_alone_element(cloned.iter_all_lines())
    #     self.assertIsInstance(cloned_line, ServiceLine)
    #     self.assertNotEqual(sl.pk, cloned_line.pk)
    #     self.assertEqual(sl.related_item, cloned_line.related_item)
    #     self.assertEqual(sl.quantity,     cloned_line.quantity)
    #     self.assertEqual(sl.unit_price,   cloned_line.unit_price)
    #
    #     # Addresses are cloned
    #     self.assertEqual(address_count + 2, Address.objects.count())
    #
    #     billing_address = cloned.billing_address
    #     self.assertIsInstance(billing_address, Address)
    #     self.assertEqual(cloned,                billing_address.owner)
    #     self.assertEqual(origin_b_addr.name,    billing_address.name)
    #     self.assertEqual(origin_b_addr.city,    billing_address.city)
    #     self.assertEqual(origin_b_addr.zipcode, billing_address.zipcode)
    #
    # def test_clone__method02(self):  # DEPRECATED
    #     "Organisation is managed => number is generated (but only once BUGFIX)."
    #     user = self.login_as_root_and_get()
    #
    #     source, target = self.create_orgas(user=user)
    #     self._set_managed(source)
    #
    #     item = self.get_object_or_fail(
    #         NumberGeneratorItem,
    #         organisation=source,
    #         numbered_type=ContentType.objects.get_for_model(SalesOrder),
    #     )
    #     item.data['format'] = 'ORD-{counter:04}'
    #     item.save()
    #
    #     order = self.create_salesorder(user=user, name='My Order', source=source, target=target)
    #     self.assertEqual('ORD-0001', order.number)
    #
    #     cloned = order.clone()
    #     self.assertEqual('ORD-0002', cloned.number)
