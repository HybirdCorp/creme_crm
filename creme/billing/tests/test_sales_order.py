from datetime import date
from decimal import Decimal

from django.template import Context, Template
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import (
    BrickDetailviewLocation,
    Currency,
    SetCredentials,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

from ..bricks import ReceivedSalesOrdersBrick
from ..constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
from ..models import SalesOrderStatus
from .base import (
    Invoice,
    Organisation,
    SalesOrder,
    _BillingTestCase,
    skipIfCustomSalesOrder,
)


@skipIfCustomOrganisation
@skipIfCustomSalesOrder
class SalesOrderTestCase(BrickTestCaseMixin, _BillingTestCase):
    @staticmethod
    def _build_related_creation_url(target):
        return reverse('billing__create_related_order', args=(target.id,))

    def test_status(self):
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

    def test_detailview01(self):
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Organisation, SalesOrder, Invoice],
        )
        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_OWN,
        )

        order = self.create_salesorder_n_orgas(user=user, name='My order')[0]
        response = self.assertGET200(order.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/view_sales_order.html')
        self.assertConvertButtons(
            response,
            [{'title': _('Convert to Invoice'), 'type': 'invoice', 'disabled': False}],
        )

    def test_detailview02(self):
        "Cannot create invoice => convert button disabled."
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Organisation, SalesOrder],  # Invoice
        )
        SetCredentials.objects.create(
            role=user.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_OWN,
        )

        order = self.create_salesorder_n_orgas(user=user, name='My order')[0]
        response = self.assertGET200(order.get_absolute_url())
        self.assertConvertButtons(
            response,
            # [{'title': _('Convert to Invoice'), 'type': 'invoice', 'disabled': True}],
            [{'title': _('Convert to Invoice'), 'disabled': True}],
        )

    def test_createview01(self):
        # user = self.login()
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

        self.assertRelationCount(1, order, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, order, REL_SUB_BILL_RECEIVED, target)

    def test_create_related01(self):
        # user = self.login()
        user = self.login_as_root_and_get()

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

        self.assertDictEqual(
            {'status': 1, self.TARGET_KEY: target},
            form.initial,
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

        self.assertRelationCount(1, order, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, order, REL_SUB_BILL_RECEIVED, target)

        self.assertEqual(order.get_absolute_url(), response.content.decode())

    def test_create_related02(self):
        "No redirection after the creation."
        # user = self.login()
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

        self.assertRelationCount(1, order, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, order, REL_SUB_BILL_RECEIVED, target)

    def test_create_related03(self):
        "Not a super-user."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[SalesOrder],
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
            set_type=SetCredentials.ESET_ALL,
        )

        source, target = self.create_orgas(user=user)
        self.assertGET200(self._build_related_creation_url(target))

    def test_create_related04(self):
        "Creation creds are needed."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            # creatable_models=[SalesOrder],
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
            set_type=SetCredentials.ESET_ALL,
        )

        source, target = self.create_orgas(user=user)
        self.assertGET403(self._build_related_creation_url(target))

    def test_create_related05(self):
        "CHANGE creds are needed."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[SalesOrder],
        )
        SetCredentials.objects.create(
            role=user.role,
            value=(
                EntityCredentials.VIEW
                # | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        source, target = self.create_orgas(user=user)
        self.assertGET403(self._build_related_creation_url(target))

    def test_editview(self):
        # user = self.login()
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
        # user = self.login()
        user = self.login_as_root_and_get()

        order1 = self.create_salesorder_n_orgas(user=user, name='Order1')[0]
        order2 = self.create_salesorder_n_orgas(user=user, name='Order2')[0]

        response = self.assertGET200(reverse('billing__list_orders'))

        with self.assertNoException():
            orders_page = response.context['page_obj']

        self.assertEqual(2, orders_page.paginator.count)
        self.assertCountEqual([order1, order2], orders_page.paginator.object_list)

    def test_delete_status(self):
        # user = self.login()
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
        # self.login()
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_no_total(
            user=user, model=SalesOrder, status_model=SalesOrderStatus,
        )

    @skipIfCustomAddress
    def test_mass_import_update(self):
        # self.login()
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_update(
            user=user, model=SalesOrder, status_model=SalesOrderStatus,
        )

    def test_brick(self):
        # user = self.login()
        user = self.login_as_root_and_get()
        BrickDetailviewLocation.objects.create_if_needed(
            brick=ReceivedSalesOrdersBrick, order=600,
            zone=BrickDetailviewLocation.RIGHT, model=Organisation,
        )

        source, target = self.create_orgas(user=user)

        response1 = self.assertGET200(target.get_absolute_url())
        brick_node1 = self.get_brick_node(
            self.get_html_tree(response1.content),
            brick=ReceivedSalesOrdersBrick,
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
            brick=ReceivedSalesOrdersBrick,
        )
        self.assertBrickTitleEqual(
            brick_node2,
            count=1,
            title='{count} Received sales order',
            plural_title='{count} Received sales orders',
        )
        self.assertListEqual(
            [_('Name'), _('Expiration date'), _('Status'), _('Total without VAT')],
            self.get_brick_table_column_titles(brick_node2),
        )
        rows = self.get_brick_table_rows(brick_node2)

        table_cells = self.get_alone_element(rows).findall('.//td')
        self.assertEqual(4, len(table_cells))
        self.assertInstanceLink(table_cells[0], entity=order)
