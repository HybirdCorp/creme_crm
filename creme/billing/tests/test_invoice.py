# -*- coding: utf-8 -*-

from datetime import date
from decimal import Decimal
from functools import partial

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.gui import actions
from creme.creme_core.models import (
    CremeEntity,
    Currency,
    Relation,
    RelationType,
    SetCredentials,
    Vat,
)
from creme.creme_core.tests.base import CremeTransactionTestCase
from creme.persons.constants import REL_SUB_CUSTOMER_SUPPLIER
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

from ..actions import ExportInvoiceAction, GenerateNumberAction
from ..constants import (  # DISCOUNT_LINE_AMOUNT DISCOUNT_PERCENT
    REL_OBJ_BILL_ISSUED,
    REL_OBJ_BILL_RECEIVED,
    REL_SUB_BILL_ISSUED,
    REL_SUB_BILL_RECEIVED,
)
from ..models import (
    AdditionalInformation,
    InvoiceStatus,
    Line,
    PaymentInformation,
    PaymentTerms,
    SettlementTerms,
)
from .base import (
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


@skipIfCustomOrganisation
@skipIfCustomInvoice
class InvoiceTestCase(_BillingTestCase):
    @staticmethod
    def _build_gennumber_url(invoice):
        return reverse('billing__generate_invoice_number', args=(invoice.id,))

    def test_source_n_target01(self):
        "Creation."
        user = self.create_user()
        name = 'Invoice001'
        source, target = self.create_orgas(user=user)
        invoice = Invoice.objects.create(
            user=user,
            name=name,
            status_id=1,
            source=source,
            target=target,
        )
        self.assertEqual(user, invoice.user)
        self.assertEqual(name, invoice.name)
        self.assertEqual(1,    invoice.status_id)

        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED, target)

        with self.assertNumQueries(0):
            gotten_source = invoice.source

        with self.assertNumQueries(0):
            gotten_target = invoice.target

        self.assertEqual(source, gotten_source)
        self.assertEqual(target, gotten_target)

        # # DEPRECATED
        # self.assertEqual(source, invoice.get_source().get_real_entity())
        # self.assertEqual(target, invoice.get_target().get_real_entity())

    def test_source_n_target02(self):
        "Errors at creation."
        user = self.create_user()
        source, target = self.create_orgas(user=user)

        build_invoice = partial(
            Invoice, user=user, name='Invoice001', status_id=1,
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

    def test_source_n_target03(self):
        "Edition."
        user = self.create_user()
        name = 'Invoice001'
        source1, target1 = self.create_orgas(user=user)
        invoice = Invoice.objects.create(
            user=user,
            name=name,
            status_id=1,
            source=source1,
            target=target1,
        )
        source2, target2 = self.create_orgas(user=user, index=2)

        # ---
        invoice = self.refresh(invoice)

        invoice.source = source2
        invoice.save()

        self.assertRelationCount(0, invoice, REL_SUB_BILL_ISSUED, source1)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED, source2)

        # ---
        invoice = self.refresh(invoice)

        invoice.target = target2
        invoice.save()

        self.assertRelationCount(0, invoice, REL_SUB_BILL_RECEIVED, target1)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED, target2)

    def test_source_n_target04(self):
        "Several save without refreshing."
        user = self.create_user()
        name = 'invoice001'
        source1, target1 = self.create_orgas(user=user)
        invoice = Invoice.objects.create(
            user=user,
            name=name,
            status_id=1,
            source=source1,
            target=target1,
        )

        # ---
        source2, target2 = self.create_orgas(user=user, index=2)
        invoice.source = source2
        invoice.target = target2
        invoice.save()

        self.assertRelationCount(0, invoice, REL_SUB_BILL_ISSUED, source1)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED, source2)

        self.assertRelationCount(0, invoice, REL_SUB_BILL_RECEIVED, target1)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED, target2)

        # ---
        source3, target3 = self.create_orgas(user=user, index=3)
        invoice.source = source3
        invoice.target = target3
        invoice.save()

        self.assertRelationCount(0, invoice, REL_SUB_BILL_ISSUED, source2)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED, source3)

        self.assertRelationCount(0, invoice, REL_SUB_BILL_RECEIVED, target2)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED, target3)

    def test_createview01(self):
        "Source is not managed."
        self.login()

        response = self.assertGET200(reverse('billing__create_invoice'))

        with self.assertNoException():
            number_f = response.context['form'].fields['number']

        self.assertFalse(number_f.help_text)

        # ---
        name = 'Invoice001'
        currency = Currency.objects.all()[0]
        terms = SettlementTerms.objects.all()[0]

        source, target = self.create_orgas()

        self.assertFalse(target.billing_address)
        self.assertFalse(target.shipping_address)

        invoice = self.create_invoice(
            name=name,
            source=source, target=target,
            currency=currency, payment_type=terms.id,
        )
        self.assertEqual(1,        invoice.status_id)
        self.assertEqual(currency, invoice.currency)
        self.assertEqual(terms,    invoice.payment_type)
        self.assertEqual(date(year=2010, month=10, day=13), invoice.expiration_date)
        self.assertEqual('', invoice.description)
        self.assertIsNone(invoice.payment_info)
        self.assertEqual('', invoice.buyers_order_number)

        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED,       source)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED,     target)
        self.assertRelationCount(1, target,  REL_SUB_CUSTOMER_SUPPLIER, source)

        self.assertEqual(source, invoice.source)
        self.assertEqual(target, invoice.target)

        target = self.refresh(target)
        self.assertIsNone(target.billing_address)
        self.assertIsNone(target.shipping_address)

        b_addr = invoice.billing_address
        self.assertEqual(invoice,              b_addr.owner)
        self.assertEqual(_('Billing address'), b_addr.name)
        self.assertEqual(_('Billing address'), b_addr.address)

        s_addr = invoice.shipping_address
        self.assertEqual(invoice,               s_addr.owner)
        self.assertEqual(_('Shipping address'), s_addr.name)
        self.assertEqual(_('Shipping address'), s_addr.address)

        self.create_invoice('Invoice002', source, target, currency)
        self.assertRelationCount(1, target, REL_SUB_CUSTOMER_SUPPLIER, source)

    def test_createview02(self):
        "Source is managed => no number anyway."
        self.login()

        source, target = self.create_orgas()
        self._set_managed(source)

        invoice = self.create_invoice('Invoice001', source, target)
        self.assertEqual('', invoice.number)

    @skipIfCustomAddress
    def test_createview_with_address(self):
        user = self.login()

        name = 'Invoice001'
        source = Organisation.objects.filter(is_managed=True)[0]
        target = Organisation.objects.create(user=user, name='Target Orga')

        create_addr = partial(Address.objects.create, owner=target)
        target.shipping_address = create_addr(
            name='ShippingAddr', address='Temple of fire',
            po_box='6565', zipcode='789', city='Konoha',
            department='dep1', state='Stuff', country='Land of Fire',
        )
        target.billing_address = create_addr(
            name='BillingAddr', address='Temple of sand',
            po_box='8778', zipcode='123', city='Suna',
            department='dep2', state='Foo', country='Land of Sand',
        )
        target.save()

        self.assertEqual(
            # source.id,
            source,
            self.client.get(reverse('billing__create_invoice'))
                       .context['form'][self.SOURCE_KEY]  # .context['form']['source']
                       .field
                       .initial
        )

        description = 'My fabulous invoice'
        b_order = '123abc'
        invoice = self.create_invoice(
            name, source, target,
            description=description,
            buyers_order_number=b_order,
        )

        self.assertEqual(description, invoice.description)
        self.assertEqual(b_order,     invoice.buyers_order_number)
        self.assertIsNone(invoice.payment_type)

        self.assertAddressContentEqual(target.billing_address, invoice.billing_address)
        self.assertEqual(invoice, invoice.billing_address.owner)

        self.assertAddressContentEqual(target.shipping_address, invoice.shipping_address)
        self.assertEqual(invoice, invoice.shipping_address.owner)

        self.assertGET200(invoice.get_absolute_url())

    def test_createview_error(self):
        "Credentials errors with Organisation."
        user = self.login(is_superuser=False, creatable_models=[Invoice])
        create_sc = partial(SetCredentials.objects.create, role=self.role)
        create_sc(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.UNLINK
            ),  # Not LINK
            set_type=SetCredentials.ESET_ALL,
        )
        create_sc(
            value=(
                EntityCredentials.VIEW
                | EntityCredentials.CHANGE
                | EntityCredentials.DELETE
                | EntityCredentials.LINK
                | EntityCredentials.UNLINK
            ),
            set_type=SetCredentials.ESET_OWN,
        )

        source = Organisation.objects.create(user=self.other_user, name='Source Orga')
        self.assertFalse(user.has_perm_to_link(source))

        target = Organisation.objects.create(user=self.other_user, name='Target Orga')
        self.assertFalse(user.has_perm_to_link(target))

        url = reverse('billing__create_invoice')
        response1 = self.client.get(url, follow=True)

        with self.assertNoException():
            form = response1.context['form']

        self.assertIn(self.SOURCE_KEY, form.fields, 'Bad form ?!')

        response2 = self.assertPOST200(
            url, follow=True,
            data={
                'user':   user.id,
                'name':  'Invoice001',
                'status': 1,

                'issuing_date':    '2011-9-7',
                'expiration_date': '2011-10-13',

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )

        link_error = _('You are not allowed to link this entity: {}')
        not_viewable_error = _('Entity #{id} (not viewable)').format
        self.assertFormError(
            response2, 'form', self.SOURCE_KEY,
            link_error.format(not_viewable_error(id=source.id)),
        )
        self.assertFormError(
            response2, 'form', self.TARGET_KEY,
            link_error.format(not_viewable_error(id=target.id)),
        )

    def test_createview_payment_info01(self):
        "One PaymentInformation in the source => used automatically."
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        pi = PaymentInformation.objects.create(organisation=source, name='RIB 1')

        invoice = self.create_invoice('Invoice001', source, target)
        self.assertEqual(pi, invoice.payment_info)

    def test_createview_payment_info02(self):
        "Several PaymentInformation in the source => default one is used."
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        create_pi = partial(PaymentInformation.objects.create, organisation=source)
        create_pi(name='RIB 1')
        pi2 = create_pi(name='RIB 2', is_default=True)
        create_pi(name='RIB 3')
        self.assertCountEqual(
            [pi2], PaymentInformation.objects.filter(organisation=source, is_default=True),
        )

        invoice = self.create_invoice('Invoice001', source, target)
        # self.assertIsNone(invoice.payment_info)
        self.assertEqual(pi2, invoice.payment_info)

    def test_create_related01(self):
        user = self.login()
        source, target = self.create_orgas()
        url = reverse('billing__create_related_invoice', args=(target.id,))
        response = self.assertGET200(url)

        context = response.context
        self.assertEqual(
            _('Create an invoice for «{entity}»').format(entity=target),
            context.get('title'),
        )
        self.assertEqual(Invoice.save_label, context.get('submit_label'))

        with self.assertNoException():
            form = context['form']

        self.assertDictEqual(
            {
                'status': 1,
                # 'target': target,  # deprecated
                self.TARGET_KEY: target,
            },
            form.initial,
        )

        # ---
        name = 'Invoice#1'
        currency = Currency.objects.all()[0]
        status = InvoiceStatus.objects.all()[1]
        response = self.client.post(
            url, follow=True,
            data={
                'user':   user.pk,
                'name':   name,
                'status': status.id,

                'issuing_date':    '2013-12-15',
                'expiration_date': '2014-1-22',

                'currency': currency.id,
                'discount': Decimal(),

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response)

        invoice = self.get_object_or_fail(Invoice, name=name)
        self.assertEqual(date(year=2013, month=12, day=15), invoice.issuing_date)
        self.assertEqual(date(year=2014, month=1,  day=22), invoice.expiration_date)
        self.assertEqual(currency, invoice.currency)
        self.assertEqual(status,   invoice.status)

        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED, target)

    def test_create_related02(self):
        "Not a super-user."
        self.login(
            is_superuser=False,
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice],
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
        self.assertGET200(
            reverse('billing__create_related_invoice', args=(target.id,)),
        )

    def test_create_related03(self):
        "Creation creds are needed."
        self.login(
            is_superuser=False,
            allowed_apps=['persons', 'billing'],
            # creatable_models=[Invoice],
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
        self.assertGET403(
            reverse('billing__create_related_invoice', args=(target.id,)),
        )

    def test_create_related04(self):
        "CHANGE creds are needed."
        self.login(
            is_superuser=False,
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice],
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
        self.assertGET403(
            reverse('billing__create_related_invoice', args=(target.id,)),
        )

    def test_listview(self):
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        invoice1 = self.create_invoice('invoice 01', source, target)
        invoice2 = self.create_invoice('invoice 02', source, target)

        response = self.assertGET200(reverse('billing__list_invoices'))

        with self.assertNoException():
            invoices_page = response.context['page_obj']

        self.assertEqual(2, invoices_page.paginator.count)
        self.assertSetEqual(
            {invoice1, invoice2},
            {*invoices_page.paginator.object_list},
        )

    def test_listview_export_actions(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice #1')[0]

        export_actions = [
            action
            for action in actions.actions_registry
                                 .instance_actions(user=user, instance=invoice)
            if isinstance(action, ExportInvoiceAction)
        ]
        self.assertEqual(1, len(export_actions))

        export_action = export_actions[0]
        self.assertEqual('billing-export_invoice', export_action.id)
        self.assertEqual('redirect', export_action.type)
        self.assertEqual(
            reverse('billing__export', args=(invoice.id,)),
            export_action.url,
        )
        self.assertTrue(export_action.is_enabled)
        self.assertTrue(export_action.is_visible)

    def test_listview_generate_number_actions(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice #1')[0]

        number_actions = [
            action
            for action in actions.actions_registry
                                 .instance_actions(user=user, instance=invoice)
            if isinstance(action, GenerateNumberAction)
        ]
        self.assertEqual(1, len(number_actions))

        number_action = number_actions[0]
        self.assertEqual('billing-generate_number', number_action.id)
        self.assertEqual('billing-invoice-number', number_action.type)
        self.assertEqual(
            reverse('billing__generate_invoice_number', args=(invoice.id,)),
            number_action.url,
        )
        self.assertTrue(number_action.is_enabled)
        self.assertTrue(number_action.is_visible)
        self.assertEqual(_('Generate the number of the Invoice'), number_action.help_text)
        self.assertEqual({
            'data': {},
            'options': {
                'confirm': _('Do you really want to generate an invoice number?'),
            },
        }, number_action.action_data)

    def test_listview_generate_number_actions_disabled(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice #1')[0]
        invoice.number = 'J03'
        invoice.save()

        number_actions = [
            action
            for action in actions.actions_registry
                                 .instance_actions(user=user, instance=invoice)
            if isinstance(action, GenerateNumberAction)
        ]
        self.assertEqual(1, len(number_actions))

        number_action = number_actions[0]
        self.assertEqual('billing-generate_number', number_action.id)
        self.assertEqual('billing-invoice-number', number_action.type)
        self.assertEqual(
            reverse('billing__generate_invoice_number', args=(invoice.id,)),
            number_action.url,
        )
        self.assertFalse(number_action.is_enabled)
        self.assertTrue(number_action.is_visible)

    def test_editview01(self):
        user = self.login()

        name = 'Invoice001'
        invoice, source1, target1 = self.create_invoice_n_orgas(name)

        url = invoice.get_edit_absolute_url()
        response1 = self.assertGET200(url)

        with self.assertNoException():
            formfields = response1.context['form'].fields
            source_f = formfields[self.SOURCE_KEY]
            target_f = formfields[self.TARGET_KEY]

        self.assertEqual(source1, source_f.initial)
        self.assertEqual(target1, target_f.initial)

        # ---
        name += '_edited'

        create_orga = partial(Organisation.objects.create, user=user)
        source2 = create_orga(name='Source Orga 2')
        target2 = create_orga(name='Target Orga 2')

        currency = Currency.objects.all()[0]
        response2 = self.client.post(
            url, follow=True,
            data={
                'user':            user.pk,
                'name':            name,
                'issuing_date':    '2010-9-7',
                'expiration_date': '2011-11-14',
                'status':          1,
                'currency':        currency.pk,
                'discount':        Decimal(),
                # 'discount_unit':   1,

                self.SOURCE_KEY: source2.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target2),
            },
        )
        self.assertNoFormError(response2)
        self.assertRedirects(response2, invoice.get_absolute_url())

        invoice = self.refresh(invoice)
        self.assertEqual(name, invoice.name)
        self.assertEqual(date(year=2011, month=11, day=14), invoice.expiration_date)
        self.assertIsNone(invoice.payment_info)

        self.assertEqual(source2, invoice.source)
        self.assertEqual(target2, invoice.target)

        self.assertRelationCount(1, source2, REL_OBJ_BILL_ISSUED,   invoice)
        self.assertRelationCount(1, target2, REL_OBJ_BILL_RECEIVED, invoice)

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_editview02(self):
        "User changes => lines user changes."
        user = self.login()

        # Simpler to test with 2 super users (do not have to create SetCredentials etc...)
        other_user = self.other_user
        other_user.superuser = True
        other_user.save()

        invoice, source, target = self.create_invoice_n_orgas('Invoice001', user=user)
        self.assertEqual(user, invoice.user)

        create_pline = partial(
            ProductLine.objects.create, user=user, related_document=invoice,
        )
        create_sline = partial(
            ServiceLine.objects.create, user=user, related_document=invoice,
        )
        lines = [
            create_pline(on_the_fly_item='otf1',             unit_price=Decimal('1')),
            create_pline(related_item=self.create_product(), unit_price=Decimal('2')),
            create_sline(on_the_fly_item='otf2',             unit_price=Decimal('4')),
            create_sline(related_item=self.create_service(), unit_price=Decimal('5')),
        ]

        response = self.client.post(
            invoice.get_edit_absolute_url(), follow=True,
            data={
                'user':   other_user.pk,
                'name':   invoice.name,
                'status': invoice.status.id,

                'expiration_date': '2011-11-14',

                'currency': invoice.currency.id,
                'discount': invoice.discount,

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response)

        invoice = self.refresh(invoice)
        self.assertEqual(other_user, invoice.user)

        self.assertListEqual(
            [other_user.id] * 4,
            [
                *CremeEntity.objects.filter(
                    pk__in=[line.pk for line in lines],
                ).values_list('user', flat=True),
            ],  # Refresh
        )

    # def test_editview04(self):
    def test_editview03(self):
        "Error on discount."
        user = self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        url = invoice.get_edit_absolute_url()

        def post(discount):
            return self.assertPOST200(
                url, follow=True,
                data={
                    'user':     user.id,
                    'name':     invoice.name,
                    'status':   invoice.status_id,
                    'currency': invoice.currency.pk,
                    'discount': discount,

                    self.SOURCE_KEY: source.id,
                    self.TARGET_KEY: self.formfield_value_generic_entity(target),
                },
            )

        msg = _('Enter a number between 0 and 100 (it is a percentage).')
        self.assertFormError(post('150'), 'form', 'discount', msg)
        self.assertFormError(post('-10'), 'form', 'discount', msg)

    def test_editview_payment_info01(self):
        user = self.login()

        source2 = Organisation.objects.create(user=user, name='Sega')
        invoice, source1, target = self.create_invoice_n_orgas('Playstations')

        pi_sony = PaymentInformation.objects.create(
            organisation=source1, name='RIB sony',
        )
        invoice.payment_info = pi_sony
        invoice.save()

        currency = Currency.objects.all()[0]
        response = self.client.post(
            invoice.get_edit_absolute_url(), follow=True,
            data={
                'user':            user.id,
                'name':            'Dreamcast',
                'issuing_date':    '2010-9-7',
                'expiration_date': '2010-10-13',
                'status':          1,
                'currency':        currency.pk,
                'discount':        Decimal(),

                self.SOURCE_KEY: source2.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response)
        self.assertIsNone(self.refresh(invoice).payment_info)

    def test_editview_payment_info02(self):
        "One PaymentInformation in the source => used automatically."
        user = self.login()

        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        pi = PaymentInformation.objects.create(organisation=source, name='RIB 1')

        response = self.client.post(
            invoice.get_edit_absolute_url(), follow=True,
            data={
                'user':   user.pk,
                'name':   invoice.name,
                'status': invoice.status.id,

                'currency': invoice.currency.id,
                'discount': invoice.discount,

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response)

        invoice = self.refresh(invoice)
        self.assertEqual(pi, invoice.payment_info)

    def test_editview_payment_info03(self):
        "Several PaymentInformation in the source => default one is used."
        user = self.login()

        invoice, source, target = self.create_invoice_n_orgas('Invoice001')

        create_pi = partial(PaymentInformation.objects.create, organisation=source)
        create_pi(name='RIB 1')
        pi2 = create_pi(name='RIB 2', is_default=True)

        response = self.client.post(
            invoice.get_edit_absolute_url(), follow=True,
            data={
                'user':   user.pk,
                'name':   invoice.name,
                'status': invoice.status.id,

                'currency': invoice.currency.id,
                'discount': invoice.discount,

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response)

        invoice = self.refresh(invoice)
        # self.assertIsNone(invoice.payment_info)
        self.assertEqual(pi2, invoice.payment_info)

    def test_inner_edit01(self):
        user = self.login()

        name = 'invoice001'
        invoice = self.create_invoice_n_orgas(name, user=user)[0]

        build_url = partial(self.build_inneredit_url, entity=invoice)
        url = build_url(fieldname='name')
        self.assertGET200(url)

        name = name.title()
        response = self.client.post(
            url,
            data={
                'entities_lbl': [str(invoice)],
                'field_value':  name,
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(invoice).name)

        # Addresses should not be editable
        self.assertGET(400, build_url(fieldname='billing_address'))
        self.assertGET(400, build_url(fieldname='shipping_address'))

    def test_inner_edit02(self):
        "Discount"
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001', user=user)[0]
        url = self.build_inneredit_url(entity=invoice, fieldname='discount')
        self.assertGET200(url)

        response = self.assertPOST200(
            url,
            data={
                'entities_lbl': [str(invoice)],
                'field_value':  '110',
            },
        )
        self.assertFormError(
            response, 'form', 'field_value',
            _('Enter a number between 0 and 100 (it is a percentage).'),
        )

    def test_generate_number01(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        self.assertFalse(invoice.number)
        self.assertEqual(1, invoice.status_id)

        issuing_date = invoice.issuing_date
        self.assertTrue(issuing_date)

        url = self._build_gennumber_url(invoice)
        self.assertGET405(url, follow=True)
        self.assertPOST200(url, follow=True)

        invoice = self.refresh(invoice)
        number = invoice.number
        status_id = invoice.status_id
        self.assertTrue(number)
        self.assertEqual(2,            status_id)
        self.assertEqual(issuing_date, invoice.issuing_date)

        # Already generated
        self.assertPOST409(url, follow=True)
        invoice = self.refresh(invoice)
        self.assertEqual(number,    invoice.number)
        self.assertEqual(status_id, invoice.status_id)

    def test_generate_number02(self):
        self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        invoice.issuing_date = None
        invoice.save()

        self.assertPOST200(self._build_gennumber_url(invoice), follow=True)
        invoice = self.refresh(invoice)
        self.assertTrue(invoice.issuing_date)
        # NB: this test can fail if run at midnight...
        self.assertEqual(date.today(), invoice.issuing_date)

    def test_generate_number03(self):
        "Managed organisation."
        self.login()

        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        self._set_managed(source)

        self.assertPOST200(self._build_gennumber_url(invoice), follow=True)
        self.assertEqual(
            settings.INVOICE_NUMBER_PREFIX + '1',
            self.refresh(invoice).number,
        )

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_get_lines01(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]
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
    def test_get_lines02(self):
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]
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
        user = self.login()
        invoice = self.create_invoice_n_orgas('Invoice001')[0]

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
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice001')[0]
        self.assertEqual(0, invoice._get_total_with_tax())

        kwargs = {'user': user, 'related_document': invoice}
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

    @skipIfCustomAddress
    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_clone(self):
        user = self.login()

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

        currency = Currency.objects.create(
            name='Martian dollar', local_symbol='M$',
            international_symbol='MUSD', is_custom=True,
        )
        invoice = self.create_invoice('Invoice001', source, target, currency=currency)
        invoice.additional_info = AdditionalInformation.objects.all()[0]
        invoice.payment_terms = PaymentTerms.objects.all()[0]
        invoice.save()

        kwargs = {'user': user, 'related_document': invoice}
        ServiceLine.objects.create(related_item=self.create_service(), **kwargs)
        ServiceLine.objects.create(on_the_fly_item='otf service', **kwargs)
        ProductLine.objects.create(related_item=self.create_product(), **kwargs)
        ProductLine.objects.create(on_the_fly_item='otf product', **kwargs)

        self.assertEqual(address_count + 2, Address.objects.count())

        origin_b_addr = invoice.billing_address
        origin_b_addr.zipcode += ' (edited)'
        origin_b_addr.save()

        origin_s_addr = invoice.shipping_address
        origin_s_addr.zipcode += ' (edited)'
        origin_s_addr.save()

        cloned = self.refresh(invoice.clone())
        invoice = self.refresh(invoice)

        self.assertNotEqual(invoice, cloned)  # Not the same pk
        self.assertEqual(invoice.name,     cloned.name)
        self.assertEqual(currency,         cloned.currency)
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

    def test_clone_source_n_target(self):
        "Internal relation-types should not be cloned."
        self.login()

        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        cloned_source = source.clone()
        cloned_target = target.clone()

        self.assertRelationCount(1, invoice, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, invoice, REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(0, invoice, REL_SUB_BILL_ISSUED,   cloned_source)
        self.assertRelationCount(0, invoice, REL_SUB_BILL_RECEIVED, cloned_target)

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_discounts(self):
        user = self.login()

        invoice = self.create_invoice_n_orgas('Invoice0001', discount=10)[0]

        kwargs = {'user': user, 'related_document': invoice}
        product_line = ProductLine.objects.create(
            on_the_fly_item='Flyyy product',
            unit_price=Decimal('1000.00'), quantity=2,
            discount=Decimal('10.00'),
            # discount_unit=DISCOUNT_PERCENT,
            discount_unit=Line.Discount.PERCENT,
            # vat_value=Vat.get_default_vat(),
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
            # discount_unit=DISCOUNT_LINE_AMOUNT,
            discount_unit=Line.Discount.LINE_AMOUNT,
            # vat_value=Vat.get_default_vat(),
            vat_value=Vat.objects.default(),
            **kwargs
        )
        self.assertEqual(90, service_line.get_price_exclusive_of_tax())

        invoice = self.refresh(invoice)
        self.assertEqual(1710, invoice._get_total())  # total_exclusive_of_tax
        self.assertEqual(1710, invoice.total_no_vat)

    # def test_delete_status01(self):
    def test_delete_status(self):
        self.login()

        new_status = InvoiceStatus.objects.first()
        status2del = InvoiceStatus.objects.create(name='OK')

        invoice = self.create_invoice_n_orgas('Nerv')[0]
        invoice.status = status2del
        invoice.save()

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='invoice_status',
            new_status=new_status,
            doc=invoice,
        )

    def test_delete_paymentterms(self):
        self.login()

        self.assertGET200(
            reverse('creme_config__model_portal', args=('billing', 'payment_terms')),
        )

        pterms = PaymentTerms.objects.create(name='3 months')

        invoice = self.create_invoice_n_orgas('Nerv')[0]
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
        self.login()

        currency = Currency.objects.create(
            name='Berry', local_symbol='B', international_symbol='BRY',
        )
        invoice = self.create_invoice_n_orgas('Nerv', currency=currency)[0]

        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'currency', currency.id)
        ))
        self.assertFormError(
            response, 'form',
            'replace_billing__invoice_currency',
            _('Deletion is not possible.'),
        )

        invoice = self.assertStillExists(invoice)
        self.assertEqual(currency, invoice.currency)

    def test_delete_additional_info(self):
        self.login()

        info = AdditionalInformation.objects.create(name='Agreement')
        invoice = self.create_invoice_n_orgas('Nerv')[0]
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

    @skipIfCustomAddress
    def test_mass_import(self):
        self.login()
        self._aux_test_csv_import(Invoice, InvoiceStatus, number_help_text=False)

    @skipIfCustomAddress
    def test_mass_import_update01(self):
        self.login()
        self._aux_test_csv_import_update(
            Invoice, InvoiceStatus,
            override_billing_addr=False,
            override_shipping_addr=True,
        )

    @skipIfCustomAddress
    def test_mass_import_update02(self):
        self.login()
        self._aux_test_csv_import_update(
            Invoice, InvoiceStatus,
            override_billing_addr=True,
            override_shipping_addr=False,
        )

    @skipIfCustomAddress
    def test_mass_import_update03(self):
        self.login()
        self._aux_test_csv_import_update(
            Invoice, InvoiceStatus,
            target_billing_address=False,
            override_billing_addr=True,
        )

    @skipIfCustomAddress
    def test_mass_import_update04(self):
        self.login()
        self._aux_test_csv_import(
            Invoice, InvoiceStatus, update=True, number_help_text=False,
        )


@skipIfCustomOrganisation
@skipIfCustomInvoice
@skipIfCustomProductLine
@skipIfCustomServiceLine
class BillingDeleteTestCase(_BillingTestCaseMixin, CremeTransactionTestCase):
    def setUp(self):  # setUpClass does not work here
        super().setUp()
        self.populate('creme_core', 'creme_config', 'billing')
        self.login()

        # NB: we need pk=1 for the default instances created by formset for detail-view.
        #     It would not be useful if we reset ID sequences...
        Vat.objects.get_or_create(id=1, value=Decimal('0.0'))

    def test_delete01(self):
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        product_line = ProductLine.objects.create(
            user=self.user,
            related_document=invoice,
            on_the_fly_item='My product',
        )
        service_line = ServiceLine.objects.create(
            user=self.user,
            related_document=invoice,
            on_the_fly_item='My service',
        )

        b_addr = invoice.billing_address
        self.assertIsInstance(b_addr, Address)

        s_addr = invoice.billing_address
        self.assertIsInstance(s_addr, Address)

        invoice.delete()
        self.assertDoesNotExist(invoice)
        self.assertDoesNotExist(product_line)
        self.assertDoesNotExist(service_line)

        self.assertStillExists(source)
        self.assertStillExists(target)

        self.assertDoesNotExist(b_addr)
        self.assertDoesNotExist(s_addr)

    def test_delete02(self):
        "Can't be deleted"
        user = self.user
        invoice, source, target = self.create_invoice_n_orgas('Invoice001')
        service_line = ServiceLine.objects.create(
            user=user, related_document=invoice, on_the_fly_item='Flyyyyy',
        )
        rel1 = Relation.objects.get(
            subject_entity=invoice.id, object_entity=service_line.id,
        )

        # This relation prohibits the deletion of the invoice
        ce = CremeEntity.objects.create(user=user)
        rtype = RelationType.objects.smart_update_or_create(
            ('test-subject_linked', 'is linked to'),
            ('test-object_linked',  'is linked to'),
            is_internal=True,
        )[0]
        rel2 = Relation.objects.create(
            subject_entity=invoice, object_entity=ce, type=rtype, user=user,
        )

        self.assertRaises(ProtectedError, invoice.delete)

        try:
            Invoice.objects.get(pk=invoice.pk)
            Organisation.objects.get(pk=source.pk)
            Organisation.objects.get(pk=target.pk)

            CremeEntity.objects.get(pk=ce.id)
            Relation.objects.get(pk=rel2.id)

            ServiceLine.objects.get(pk=service_line.pk)
            Relation.objects.get(pk=rel1.id)
        except Exception as e:
            self.fail(f'Exception: ({e}). Maybe the db does not support transaction?')
