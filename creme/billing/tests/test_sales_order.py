# -*- coding: utf-8 -*-

from datetime import date
from decimal import Decimal

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.models import Currency, SetCredentials
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

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
class SalesOrderTestCase(_BillingTestCase):
    @staticmethod
    def _build_related_creation_url(target):
        return reverse('billing__create_related_order', args=(target.id,))

    def test_detailview01(self):
        self.login(
            is_superuser=False,
            allowed_apps=['billing', 'persons'],
            creatable_models=[Organisation, SalesOrder, Invoice],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_OWN,
        )

        order = self.create_salesorder_n_orgas('My order')[0]
        response = self.assertGET200(order.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/view_sales_order.html')
        self.assertConvertButtons(
            response,
            [{'title': _('Convert to Invoice'), 'type': 'invoice', 'disabled': False}],
        )

    def test_detailview02(self):
        "Cannot create invoice => convert button disabled."
        self.login(
            is_superuser=False,
            allowed_apps=['billing', 'persons'],
            creatable_models=[Organisation, SalesOrder],  # Invoice
        )
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_OWN,
        )

        order = self.create_salesorder_n_orgas('My order')[0]
        response = self.assertGET200(order.get_absolute_url())
        self.assertConvertButtons(
            response,
            [{'title': _('Convert to Invoice'), 'type': 'invoice', 'disabled': True}],
        )

    def test_createview01(self):
        self.login()
        self.assertGET200(reverse('billing__create_order'))

        currency = Currency.objects.all()[0]
        status   = SalesOrderStatus.objects.all()[1]
        order, source, target = self.create_salesorder_n_orgas('My Sales Order', currency, status)
        self.assertEqual(date(year=2012, month=1, day=5),  order.issuing_date)
        self.assertEqual(date(year=2012, month=2, day=15), order.expiration_date)
        self.assertEqual(currency,                         order.currency)
        self.assertEqual(status,                           order.status)

        self.assertRelationCount(1, order, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, order, REL_SUB_BILL_RECEIVED, target)

    def test_create_related01(self):
        user = self.login()

        source, target = self.create_orgas()
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
            {
                'status': 1,
                # 'target': target,
                self.TARGET_KEY: target,
            },
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
                'issuing_date':    '2013-12-13',
                'expiration_date': '2014-1-20',
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
        user = self.login()

        source, target = self.create_orgas()
        name = 'Order#1'
        currency = Currency.objects.all()[0]
        status = SalesOrderStatus.objects.all()[1]
        response = self.client.post(
            self._build_related_creation_url(target) + '?redirection=false',
            follow=True,
            data={
                'user':            user.pk,
                'name':            name,
                'issuing_date':    '2013-12-13',
                'expiration_date': '2014-1-20',
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
        self.login(
            is_superuser=False,
            allowed_apps=['persons', 'billing'],
            creatable_models=[SalesOrder],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        source, target = self.create_orgas()
        self.assertGET200(self._build_related_creation_url(target))

    def test_create_related04(self):
        "Creation creds are needed."
        self.login(
            is_superuser=False,
            allowed_apps=['persons', 'billing'],
            # creatable_models=[SalesOrder],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        source, target = self.create_orgas()
        self.assertGET403(self._build_related_creation_url(target))

    def test_create_related05(self):
        "CHANGE creds are needed."
        self.login(
            is_superuser=False,
            allowed_apps=['persons', 'billing'],
            creatable_models=[SalesOrder],
        )
        SetCredentials.objects.create(
            role=self.role,
            value=(
                EntityCredentials.VIEW
                # | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_ALL,
        )

        source, target = self.create_orgas()
        self.assertGET403(self._build_related_creation_url(target))

    def test_editview(self):
        user = self.login()

        name = 'my sales order'
        order, source, target = self.create_salesorder_n_orgas(name)

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
                'issuing_date':    '2012-2-12',
                'expiration_date': '2012-3-13',
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
        self.login()

        order1 = self.create_salesorder_n_orgas('Order1')[0]
        order2 = self.create_salesorder_n_orgas('Order2')[0]

        response = self.assertGET200(reverse('billing__list_orders'))

        with self.assertNoException():
            orders_page = response.context['page_obj']

        self.assertEqual(2, orders_page.paginator.count)
        self.assertSetEqual({order1, order2}, {*orders_page.paginator.object_list})

    def test_delete_status(self):
        self.login()
        new_status = SalesOrderStatus.objects.first()
        status2del = SalesOrderStatus.objects.create(name='OK')

        order = self.create_salesorder_n_orgas('Order', status=status2del)[0]

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='sales_order_status',
            new_status=new_status,
            doc=order,
        )

    @skipIfCustomAddress
    def test_mass_import(self):
        self.login()
        self._aux_test_csv_import(SalesOrder, SalesOrderStatus)

    @skipIfCustomAddress
    def test_mass_import_update(self):
        self.login()
        self._aux_test_csv_import_update(SalesOrder, SalesOrderStatus)
