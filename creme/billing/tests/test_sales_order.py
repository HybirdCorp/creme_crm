# -*- coding: utf-8 -*-

try:
    from datetime import date
    from decimal import Decimal

    from django.urls import reverse
    from django.utils.translation import ugettext as _

    from creme.creme_core.auth.entity_credentials import EntityCredentials
    from creme.creme_core.models import Currency, SetCredentials

    from creme.persons.tests.base import skipIfCustomOrganisation, skipIfCustomAddress

    from ..constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
    from ..models import SalesOrderStatus

    from .base import _BillingTestCase, skipIfCustomSalesOrder, SalesOrder, Organisation, Invoice
except Exception as e:
    print('Error in <{}>: {}'.format(__name__, e))


@skipIfCustomOrganisation
@skipIfCustomSalesOrder
class SalesOrderTestCase(_BillingTestCase):
    def test_detailview01(self):
        self.login(is_superuser=False,
                   allowed_apps=['billing', 'persons'],
                   creatable_models=[Organisation, SalesOrder, Invoice],
                  )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW |
                                            EntityCredentials.LINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        order = self.create_salesorder_n_orgas('My order')[0]
        response = self.assertGET200(order.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/view_sales_order.html')
        self.assertContains(response, '<form id="id_convert2invoice"')

    def test_detailview02(self):
        "Cannot create invoice => convert button disabled"
        self.login(is_superuser=False,
                   allowed_apps=['billing', 'persons'],
                   creatable_models=[Organisation, SalesOrder],  # Invoice
                  )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW |
                                            EntityCredentials.LINK,
                                      set_type=SetCredentials.ESET_OWN
                                     )

        order = self.create_salesorder_n_orgas('My order')[0]
        response = self.assertGET200(order.get_absolute_url())
        self.assertContains(response, _('Convert to Invoice'))
        self.assertNotContains(response, '<form id="id_convert2invoice"')

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
        url = reverse('billing__create_related_order', args=(target.id,))
        response = self.assertGET200(url)
        # self.assertTemplateUsed(response, 'creme_core/generics/blockform/add_popup.html')
        self.assertTemplateUsed(response, 'creme_core/generics/blockform/add-popup.html')

        context = response.context
        # self.assertEqual(_('Create a salesorder for «%s»') % target, context.get('title'))
        self.assertEqual(_('Create a salesorder for «{entity}»').format(entity=target),
                         context.get('title')
                        )
        self.assertEqual(SalesOrder.save_label, context.get('submit_label'))

        with self.assertNoException():
            form = context['form']

        self.assertEqual({'status': 1,
                          'target': target
                         },
                         form.initial
                        )

        # ---
        name = 'Order#1'
        currency = Currency.objects.all()[0]
        status   = SalesOrderStatus.objects.all()[1]
        response = self.client.post(url, follow=True,
                                    data={'user':            user.pk,
                                          'name':            name,
                                          'issuing_date':    '2013-12-13',
                                          'expiration_date': '2014-1-20',
                                          'status':          status.id,
                                          'currency':        currency.id,
                                          'discount':        Decimal(),
                                          'source':          source.id,
                                          'target':          self.formfield_value_generic_entity(target),
                                         }
                                   )
        self.assertNoFormError(response)

        order = self.get_object_or_fail(SalesOrder, name=name)
        self.assertEqual(date(year=2013, month=12, day=13), order.issuing_date)
        self.assertEqual(date(year=2014, month=1,  day=20), order.expiration_date)
        self.assertEqual(currency, order.currency)
        self.assertEqual(status,   order.status)

        self.assertRelationCount(1, order, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, order, REL_SUB_BILL_RECEIVED, target)

    def test_create_related02(self):
        "Not a super-user"
        self.login(is_superuser=False,
                   allowed_apps=['persons', 'billing'],
                   creatable_models=[SalesOrder],
                  )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_ALL
                                     )

        source, target = self.create_orgas()
        self.assertGET200(reverse('billing__create_related_order', args=(target.id,)))

    def test_create_related03(self):
        "Creation creds are needed"
        self.login(is_superuser=False,
                   allowed_apps=['persons', 'billing'],
                   # creatable_models=[SalesOrder],
                  )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_ALL
                                     )

        source, target = self.create_orgas()
        self.assertGET403(reverse('billing__create_related_order', args=(target.id,)))

    def test_create_related04(self):
        "CHANGE creds are needed"
        self.login(is_superuser=False,
                   allowed_apps=['persons', 'billing'],
                   creatable_models=[SalesOrder],
                  )
        SetCredentials.objects.create(role=self.role,
                                      value=EntityCredentials.VIEW   |
                                            # EntityCredentials.CHANGE |
                                            EntityCredentials.DELETE |
                                            EntityCredentials.LINK   |
                                            EntityCredentials.UNLINK,
                                      set_type=SetCredentials.ESET_ALL
                                     )

        source, target = self.create_orgas()
        self.assertGET403(reverse('billing__create_related_order', args=(target.id,)))

    def test_editview(self):
        user = self.login()

        name = 'my sales order'
        order, source, target = self.create_salesorder_n_orgas(name)

        url = order.get_edit_absolute_url()
        self.assertGET200(url)

        name     = name.title()
        currency = Currency.objects.create(name='Marsian dollar', local_symbol='M$',
                                           international_symbol='MUSD', is_custom=True,
                                          )
        status   = SalesOrderStatus.objects.all()[1]
        response = self.client.post(url, follow=True,
                                    data={'user':            user.pk,
                                          'name':            name,
                                          'issuing_date':    '2012-2-12',
                                          'expiration_date': '2012-3-13',
                                          'status':          status.id,
                                          'currency':        currency.id,
                                          'discount':        Decimal(),
                                          'source':          source.id,
                                          'target':          self.formfield_value_generic_entity(target),
                                         }
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
            orders_page = response.context['entities']

        self.assertEqual(2, orders_page.paginator.count)
        self.assertEqual({order1, order2}, set(orders_page.paginator.object_list))

    def test_delete_status01(self):
        self.login()

        status = SalesOrderStatus.objects.create(name='OK')
        self.assertDeleteStatusOK(status, 'sales_order_status')

    def test_delete_status02(self):
        self.login()

        status = SalesOrderStatus.objects.create(name='OK')
        order = self.create_salesorder_n_orgas('Order', status=status)[0]

        self.assertDeleteStatusKO(status, 'sales_order_status', order)

    @skipIfCustomAddress
    def test_csv_import(self):
        self.login()
        self._aux_test_csv_import(SalesOrder, SalesOrderStatus)

    @skipIfCustomAddress
    def test_csv_import_update(self):
        self.login()
        self._aux_test_csv_import_update(SalesOrder, SalesOrderStatus)
