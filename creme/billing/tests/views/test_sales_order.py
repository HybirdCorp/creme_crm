from datetime import date
from decimal import Decimal

from django.urls import reverse
from django.utils.translation import gettext as _

from creme.billing import bricks as billing_bricks
from creme.billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
from creme.billing.models import SalesOrderStatus
from creme.creme_core.models import Currency, Relation
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.tests.base import skipIfCustomOrganisation

from ..base import (
    Invoice,
    Organisation,
    SalesOrder,
    _BillingTestCase,
    skipIfCustomSalesOrder,
)


@skipIfCustomOrganisation
@skipIfCustomSalesOrder
class SalesOrderViewsTestCase(BrickTestCaseMixin, _BillingTestCase):
    @staticmethod
    def _build_related_creation_url(target):
        return reverse('billing__create_related_order', args=(target.id,))

    def test_detail_view(self):
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

    def test_detail_view__no_convert_to_invoice(self):
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
    def test_detail_view__linked_opportunity(self):
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

    def test_creation(self):
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

    def test_related_creation(self):
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

    def test_related_creation__no_redirection(self):
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

    def test_related_creation__creation_perms(self):
        "Creation creds are needed."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            # creatable_models=[SalesOrder],
        )
        self.add_credentials(user.role, all='*')

        source, target = self.create_orgas(user=user)
        self.assertGET403(self._build_related_creation_url(target))

    def test_related_creation__change_perms(self):
        "CHANGE creds are needed."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[SalesOrder],
        )
        self.add_credentials(user.role, all='!CHANGE')

        source, target = self.create_orgas(user=user)
        self.assertGET403(self._build_related_creation_url(target))

    def test_edition(self):
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

    def test_list_view(self):
        user = self.login_as_root_and_get()

        order1 = self.create_salesorder_n_orgas(user=user, name='Order1')[0]
        order2 = self.create_salesorder_n_orgas(user=user, name='Order2')[0]

        response = self.assertGET200(reverse('billing__list_orders'))

        with self.assertNoException():
            orders_page = response.context['page_obj']

        self.assertEqual(2, orders_page.paginator.count)
        self.assertCountEqual([order1, order2], orders_page.paginator.object_list)
