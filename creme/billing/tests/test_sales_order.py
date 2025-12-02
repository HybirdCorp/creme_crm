from datetime import date
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import (
    BrickDetailviewLocation,
    Currency,
    Relation,
    Vat,
)
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

from .. import bricks as billing_bricks
from ..constants import (
    REL_SUB_BILL_ISSUED,
    REL_SUB_BILL_RECEIVED,
    UUID_ORDER_STATUS_ISSUED,
)
from ..models import Line, NumberGeneratorItem, SalesOrderStatus
from .base import (
    Address,
    Invoice,
    Organisation,
    ProductLine,
    SalesOrder,
    ServiceLine,
    _BillingTestCase,
    skipIfCustomSalesOrder,
    skipIfCustomServiceLine,
)


@skipIfCustomOrganisation
@skipIfCustomSalesOrder
class SalesOrderTestCase(BrickTestCaseMixin, _BillingTestCase):
    @staticmethod
    def _build_related_creation_url(target):
        return reverse('billing__create_related_order', args=(target.id,))

    def test_status(self):
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

    def test_status_render(self):
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

    def test_detailview(self):
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Organisation, SalesOrder, Invoice],
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        order, emitter, receiver = self.create_salesorder_n_orgas(
            user=user, name='My order 0001',
        )
        response = self.assertGET200(order.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/view_sales_order.html')

        tree = self.get_html_tree(response.content)
        self.assertConvertButtons(
            tree,
            [{'title': _('Convert to Invoice'), 'type': 'invoice', 'disabled': False}],
        )
        self.get_brick_node(tree, brick=billing_bricks.ProductLinesBrick)
        self.get_brick_node(tree, brick=billing_bricks.ServiceLinesBrick)
        self.get_brick_node(tree, brick=billing_bricks.TargetBrick)
        self.get_brick_node(tree, brick=billing_bricks.TotalBrick)

        hat_brick_node = self.get_brick_node(
            tree, brick=billing_bricks.SalesOrderCardHatBrick,
        )
        self.assertInstanceLink(hat_brick_node, entity=emitter)
        self.assertInstanceLink(hat_brick_node, entity=receiver)

    def test_detailview__no_convert_to_invoice(self):
        "Cannot create invoice => convert button disabled."
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Organisation, SalesOrder],  # Invoice
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        order = self.create_salesorder_n_orgas(user=user, name='My order')[0]
        response = self.assertGET200(order.get_absolute_url())
        self.assertConvertButtons(
            self.get_html_tree(response.content),
            [{'title': _('Convert to Invoice'), 'disabled': True}],
        )

    @skipIfNotInstalled('creme.opportunities')
    def test_detailview__linked_opportunity(self):
        from creme.opportunities import get_opportunity_model
        from creme.opportunities.constants import REL_SUB_LINKED_SALESORDER
        from creme.opportunities.models import SalesPhase

        user = self.login_as_root_and_get()
        order, emitter, receiver = self.create_salesorder_n_orgas(
            user=user, name='My order 0001',
        )
        opp = get_opportunity_model().objects.create(
            user=user, name='Linked opp',
            sales_phase=SalesPhase.objects.all()[0],
            emitter=emitter, target=receiver,
        )

        Relation.objects.create(
            subject_entity=order,
            type_id=REL_SUB_LINKED_SALESORDER,
            object_entity=opp,
            user=user,
        )

        response = self.assertGET200(order.get_absolute_url())

        hat_brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.SalesOrderCardHatBrick,
        )
        self.assertInstanceLink(hat_brick_node, entity=opp)

    def test_create(self):
        user = self.login_as_root_and_get()
        self.assertGET200(reverse('billing__create_order'))

        currency = Currency.objects.all()[0]
        status   = SalesOrderStatus.objects.all()[1]
        order, source, target = self.create_salesorder_n_orgas(
            user=user, name='My Sales Order', currency=currency, status=status,
        )
        self.assertEqual(date(year=2012, month=1, day=5),  order.issuing_date)
        self.assertEqual(date(year=2012, month=2, day=15), order.expiration_date)
        self.assertEqual(currency,                         order.currency)
        self.assertEqual(status,                           order.status)

        self.assertHaveRelation(subject=order, type=REL_SUB_BILL_ISSUED,   object=source)
        self.assertHaveRelation(subject=order, type=REL_SUB_BILL_RECEIVED, object=target)

    def test_create_related(self):
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[SalesOrder],
        )
        self.add_credentials(user.role, all='*')

        source, target = self.create_orgas(user=user)
        url = self._build_related_creation_url(target) + '?redirection=true'
        response = self.assertGET200(url)
        context = response.context
        self.assertEqual(
            _('Create a salesorder for «{entity}»').format(entity=target),
            context.get('title'),
        )
        self.assertEqual(SalesOrder.save_label, context.get('submit_label'))

        with self.assertNoException():
            form = context['form']
            status_f = form.fields['status']

        self.assertDictEqual(
            # {'status': 1, self.TARGET_KEY: target},
            {self.TARGET_KEY: target},
            form.initial,
        )
        # self.assertEqual(1, status_f.get_bound_field(form, 'status').initial)
        self.assertEqual(
            SalesOrderStatus.objects.default().id,
            status_f.get_bound_field(form, 'status').initial,
        )

        # ---
        name = 'Order#1'
        currency = Currency.objects.all()[0]
        status = SalesOrderStatus.objects.all()[1]
        response = self.client.post(
            url, follow=True,
            data={
                'user':            user.pk,
                'name':            name,
                'issuing_date':    self.formfield_value_date(2013, 12, 13),
                'expiration_date': self.formfield_value_date(2014,  1, 20),
                'status':          status.id,
                'currency':        currency.id,
                'discount':        Decimal(),

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response)

        order = self.get_object_or_fail(SalesOrder, name=name)
        self.assertEqual(date(year=2013, month=12, day=13), order.issuing_date)
        self.assertEqual(date(year=2014, month=1,  day=20), order.expiration_date)
        self.assertEqual(currency, order.currency)
        self.assertEqual(status,   order.status)

        self.assertHaveRelation(subject=order, type=REL_SUB_BILL_ISSUED,   object=source)
        self.assertHaveRelation(subject=order, type=REL_SUB_BILL_RECEIVED, object=target)

        self.assertEqual(order.get_absolute_url(), response.text)

    def test_create_related__no_redirection(self):
        "No redirection after the creation."
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        name = 'Order#1'
        currency = Currency.objects.all()[0]
        status = SalesOrderStatus.objects.all()[1]
        response = self.client.post(
            self._build_related_creation_url(target) + '?redirection=false',
            follow=True,
            data={
                'user':            user.pk,
                'name':            name,
                'issuing_date':    self.formfield_value_date(2013, 12, 13),
                'expiration_date': self.formfield_value_date(2014,  1, 20),
                'status':          status.id,
                'currency':        currency.id,
                'discount':        Decimal(),

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response)
        self.assertFalse(response.content)  # NB: means "close the popup"

        order = self.get_object_or_fail(SalesOrder, name=name)
        self.assertEqual(date(year=2013, month=12, day=13), order.issuing_date)
        self.assertEqual(date(year=2014, month=1,  day=20), order.expiration_date)
        self.assertEqual(currency, order.currency)
        self.assertEqual(status,   order.status)

        self.assertHaveRelation(subject=order, type=REL_SUB_BILL_ISSUED,   object=source)
        self.assertHaveRelation(subject=order, type=REL_SUB_BILL_RECEIVED, object=target)

    def test_create_related__creation_perms(self):
        "Creation creds are needed."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            # creatable_models=[SalesOrder],
        )
        self.add_credentials(user.role, all='*')

        source, target = self.create_orgas(user=user)
        self.assertGET403(self._build_related_creation_url(target))

    def test_create_related__change_perms(self):
        "CHANGE creds are needed."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[SalesOrder],
        )
        self.add_credentials(user.role, all='!CHANGE')

        source, target = self.create_orgas(user=user)
        self.assertGET403(self._build_related_creation_url(target))

    def test_edit(self):
        user = self.login_as_root_and_get()

        name = 'my sales order'
        order, source, target = self.create_salesorder_n_orgas(user=user, name=name)

        url = order.get_edit_absolute_url()
        self.assertGET200(url)

        name = name.title()
        currency = Currency.objects.create(
            name='Martian dollar', local_symbol='M$',
            international_symbol='MUSD', is_custom=True,
        )
        status = SalesOrderStatus.objects.all()[1]
        response = self.client.post(
            url, follow=True,
            data={
                'user':            user.pk,
                'name':            name,
                'issuing_date':    self.formfield_value_date(2012, 2, 12),
                'expiration_date': self.formfield_value_date(2012, 3, 13),
                'status':          status.id,
                'currency':        currency.id,
                'discount':        Decimal(),

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response)

        order = self.refresh(order)
        self.assertEqual(name,                             order.name)
        self.assertEqual(date(year=2012, month=2, day=12), order.issuing_date)
        self.assertEqual(date(year=2012, month=3, day=13), order.expiration_date)
        self.assertEqual(currency,                         order.currency)
        self.assertEqual(status,                           order.status)

    def test_listview(self):
        user = self.login_as_root_and_get()

        order1 = self.create_salesorder_n_orgas(user=user, name='Order1')[0]
        order2 = self.create_salesorder_n_orgas(user=user, name='Order2')[0]

        response = self.assertGET200(reverse('billing__list_orders'))

        with self.assertNoException():
            orders_page = response.context['page_obj']

        self.assertEqual(2, orders_page.paginator.count)
        self.assertCountEqual([order1, order2], orders_page.paginator.object_list)

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
    def test_mass_import(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_no_total(
            user=user, model=SalesOrder, status_model=SalesOrderStatus,
        )

    @skipIfCustomAddress
    def test_mass_import__update(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_update(
            user=user, model=SalesOrder, status_model=SalesOrderStatus,
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

    def test_brick(self):
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
