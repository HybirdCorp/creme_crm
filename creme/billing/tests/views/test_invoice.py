from datetime import date
from decimal import Decimal
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.billing import bricks as billing_bricks
from creme.billing.constants import (
    REL_OBJ_BILL_ISSUED,
    REL_OBJ_BILL_RECEIVED,
    REL_SUB_BILL_ISSUED,
    REL_SUB_BILL_RECEIVED,
)
from creme.billing.models import (
    InvoiceStatus,
    NumberGeneratorItem,
    PaymentInformation,
    SettlementTerms,
)
from creme.billing.setting_keys import emitter_edition_key
from creme.creme_core.forms import CreatorEntityField, ReadonlyMessageField
from creme.creme_core.models import (
    CremeEntity,
    Currency,
    Relation,
    SettingValue,
)
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.constants import REL_SUB_CUSTOMER_SUPPLIER
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

from ..base import (
    Address,
    Contact,
    Invoice,
    Organisation,
    ProductLine,
    ServiceLine,
    _BillingTestCase,
    skipIfCustomInvoice,
    skipIfCustomProductLine,
    skipIfCustomServiceLine,
)


@skipIfCustomOrganisation
@skipIfCustomInvoice
class InvoiceMiscViewsTestCase(BrickTestCaseMixin, _BillingTestCase):
    def test_detail_view(self):
        user = self.login_as_root_and_get()
        SettingValue.objects.set_4_key(emitter_edition_key, True)

        name = 'Invoice 001'
        invoice, emitter, receiver = self.create_invoice_n_orgas(
            user=user, name=name,
            status=InvoiceStatus.objects.filter(pending_payment=False)[0],
        )

        url = invoice.get_absolute_url()
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'billing/view_invoice.html')

        tree1 = self.get_html_tree(response1.content)
        self.assertConvertButtons(tree1, [])

        self.get_brick_node(tree1, brick=billing_bricks.ProductLinesBrick)
        self.get_brick_node(tree1, brick=billing_bricks.ServiceLinesBrick)
        self.get_brick_node(tree1, brick=billing_bricks.TargetBrick)
        self.get_brick_node(tree1, brick=billing_bricks.TotalBrick)

        hat_brick_node1 = self.get_brick_node(
            tree1, brick=billing_bricks.InvoiceCardHatBrick,
        )
        self.assertInstanceLink(hat_brick_node1, entity=emitter)
        self.assertInstanceLink(hat_brick_node1, entity=receiver)

        indicator_path = (
            './/div[@class="business-card-indicator business-card-warning-indicator"]'
        )
        self.assertIsNone(hat_brick_node1.find(indicator_path))

        # Expiration passed ---
        invoice.status = InvoiceStatus.objects.filter(pending_payment=True)[0]
        invoice.save()
        response2 = self.assertGET200(url)
        hat_brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content),
            brick=billing_bricks.InvoiceCardHatBrick,
        )
        indicator_node = self.get_html_node_or_fail(hat_brick_node2, indicator_path)
        self.assertEqual(_('Expiration date passed'), indicator_node.text.strip())

    @skipIfNotInstalled('creme.opportunities')
    def test_detail_view__linked_opportunity(self):
        from creme.opportunities import get_opportunity_model
        from creme.opportunities.constants import REL_SUB_LINKED_INVOICE
        from creme.opportunities.models import SalesPhase

        user = self.login_as_root_and_get()
        invoice, emitter, receiver = self.create_invoice_n_orgas(
            user=user, name='Invoice 0001',
        )
        opp = get_opportunity_model().objects.create(
            user=user, name='Linked opp',
            sales_phase=SalesPhase.objects.all()[0],
            emitter=emitter, target=receiver,
        )

        Relation.objects.create(
            subject_entity=invoice,
            type_id=REL_SUB_LINKED_INVOICE,
            object_entity=opp,
            user=user,
        )

        response = self.assertGET200(invoice.get_absolute_url())
        hat_brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.InvoiceCardHatBrick,
        )
        self.assertInstanceLink(hat_brick_node, entity=opp)

    def test_detail_view__generated_invoices(self):
        user = self.login_as_root_and_get()

        quote = self.create_quote_n_orgas(user=user, name='Quote 001')[0]

        self._convert(200, quote, 'invoice')
        invoice = self.get_alone_element(Invoice.objects.all())

        response = self.assertGET200(invoice.get_absolute_url())
        hat_brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.InvoiceCardHatBrick,
        )
        self.assertInstanceLink(hat_brick_node, entity=quote)

    def test_list_view(self):
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        invoice1 = self.create_invoice(user=user, name='invoice 01', source=source, target=target)
        invoice2 = self.create_invoice(user=user, name='invoice 02', source=source, target=target)

        response = self.assertGET200(reverse('billing__list_invoices'))

        with self.assertNoException():
            invoices_page = response.context['page_obj']

        self.assertEqual(2, invoices_page.paginator.count)
        self.assertCountEqual(
            [invoice1, invoice2],
            invoices_page.paginator.object_list,
        )


@skipIfCustomOrganisation
@skipIfCustomInvoice
class InvoiceCreationTestCase(_BillingTestCase):
    def test_organisation_target__no_address(self):
        user = self.login_as_root_and_get()

        # GET ---
        self.assertGET200(reverse('billing__create_invoice'))

        # POST ---
        name = 'Invoice001'
        currency = Currency.objects.all()[0]
        terms = SettlementTerms.objects.all()[0]
        status = InvoiceStatus.objects.first()

        source, target = self.create_orgas(user=user)

        self.assertFalse(target.billing_address)
        self.assertFalse(target.shipping_address)

        invoice = self.create_invoice(
            user=user, name=name,
            source=source, target=target,
            currency=currency, payment_type=terms.id, status=status,
        )
        self.assertEqual(status,   invoice.status)
        self.assertEqual(currency, invoice.currency)
        self.assertEqual(terms,    invoice.payment_type)
        self.assertEqual(date(year=2010, month=10, day=13), invoice.expiration_date)
        self.assertEqual('', invoice.number)
        self.assertEqual('', invoice.description)
        self.assertIsNone(invoice.payment_info)
        self.assertEqual('', invoice.buyers_order_number)

        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_ISSUED,   object=source)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_RECEIVED, object=target)
        # NB: workflow
        self.assertHaveRelation(subject=target, type=REL_SUB_CUSTOMER_SUPPLIER, object=source)

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

        self.create_invoice(
            user=user, name='Invoice002', source=source, target=target, currency=currency,
        )
        self.assertHaveRelation(subject=target, type=REL_SUB_CUSTOMER_SUPPLIER, object=source)

    @skipIfCustomAddress
    def test_organisation_target__addresses(self):
        user = self.login_as_root_and_get()

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
            source,
            self.client.get(reverse('billing__create_invoice'))
                       .context['form'][self.SOURCE_KEY]
                       .field
                       .initial,
        )

        description = 'My fabulous invoice'
        b_order = '123abc'
        invoice = self.create_invoice(
            user=user, name=name, source=source, target=target,
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

    def test_contact_target(self):
        "Workflow for Contact too."
        user = self.login_as_root_and_get()

        orga = Organisation.objects.create(user=user, name='Acme')
        contact = Contact.objects.create(user=user, first_name='John', last_name='Doe')

        invoice = self.create_invoice(
            user=user, name='Invoice-001', source=orga, target=contact,
        )
        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_ISSUED,   object=orga)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_RECEIVED, object=contact)
        # NB: workflow
        self.assertHaveRelation(subject=contact, type=REL_SUB_CUSTOMER_SUPPLIER, object=orga)

        self.assertEqual(orga, invoice.source)
        self.assertEqual(contact, invoice.target)

    def test_error(self):
        "Credentials errors with Organisation."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'], creatable_models=[Invoice],
        )
        self.add_credentials(user.role, all='!LINK', own='*')

        other_user = self.get_root_user()
        source = Organisation.objects.create(user=other_user, name='Source Orga')
        self.assertFalse(user.has_perm_to_link(source))

        target = Organisation.objects.create(user=other_user, name='Target Orga')
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
                'status': InvoiceStatus.objects.first().id,

                'issuing_date':    self.formfield_value_date(2011,  9,  7),
                'expiration_date': self.formfield_value_date(2011, 10, 13),

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )

        form = response2.context['form']
        link_error = _('You are not allowed to link this entity: {}')
        self.assertFormError(
            form,
            field=self.SOURCE_KEY,
            errors=link_error.format(source),
        )
        self.assertFormError(
            form,
            field=self.TARGET_KEY,
            errors=link_error.format(target),
        )

    def test_payment_info(self):
        "One PaymentInformation in the source => used automatically."
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        pi = PaymentInformation.objects.create(organisation=source, name='RIB 1')

        invoice = self.create_invoice(user=user, name='Invoice001', source=source, target=target)
        self.assertEqual(pi, invoice.payment_info)

    def test_payment_info__several(self):
        "Several PaymentInformation in the source => default one is used."
        user = self.login_as_root_and_get()

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

        invoice = self.create_invoice(user=user, name='Invoice001', source=source, target=target)
        self.assertEqual(pi2, invoice.payment_info)

    def test_number__emitter_not_managed__number_not_filled(self):
        user = self.login_as_root_and_get()

        response = self.assertGET200(reverse('billing__create_invoice'))

        with self.assertNoException():
            number_f = response.context['form'].fields['number']

        self.assertFalse(number_f.help_text)

        # ---
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice 001')[0]
        self.assertEqual('', invoice.number)

    def test_number__emitter_not_managed__number_filled(self):
        user = self.login_as_root_and_get()

        number = 'INV0001'
        invoice = self.create_invoice_n_orgas(user=user, name='Inv#1', number=number)[0]
        self.assertEqual(number, invoice.number)

    def test_number__managed_emitter__number_edition_allowed(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        number = 'INV0001'
        invoice = self.create_invoice(
            user=user, name='Invoice001', source=source, target=target,
            number=number,
        )
        self.assertEqual(number, invoice.number)

    def test_number__managed_emitter__number_edition_forbidden(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=source,
            numbered_type=ContentType.objects.get_for_model(Invoice),
        )
        self.assertTrue(item.is_edition_allowed)

        item.is_edition_allowed = False
        item.save()

        # Error ---
        name = 'Invoice001'
        currency = Currency.objects.all()[0]
        response = self.client.post(
            reverse('billing__create_invoice'),
            follow=True,
            data={
                'user': user.pk,
                'name': name,
                'status': InvoiceStatus.objects.first().id,

                'currency': currency.id,
                'discount': '0',

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),

                'number': 'IN010',  # <====
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='number',
            errors=_('The number is set as not editable by the configuration.'),
        )

        # OK ---
        invoice = self.create_invoice(
            user=user, name=name, source=source, target=target, currency=currency,
        )
        self.assertEqual('', invoice.number)


@skipIfCustomOrganisation
@skipIfCustomInvoice
class InvoiceRelatedCreationTestCase(_BillingTestCase):
    def test_main(self):
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user=user)
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
            status_f = form.fields['status']

        self.assertDictEqual({self.TARGET_KEY: target}, form.initial)
        self.assertEqual(
            InvoiceStatus.objects.default().id,
            status_f.get_bound_field(form, 'status').initial,
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

                'issuing_date':    self.formfield_value_date(2013, 12, 15),
                'expiration_date': self.formfield_value_date(2014,  1, 22),

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

        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_ISSUED,   object=source)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_RECEIVED, object=target)

    def test_not_superuser(self):
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice],
        )
        self.add_credentials(user.role, all='*')

        source, target = self.create_orgas(user=user)
        self.assertGET200(
            reverse('billing__create_related_invoice', args=(target.id,)),
        )

    def test_creation_perm(self):
        "Creation creds are needed."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            # creatable_models=[Invoice],
        )
        self.add_credentials(user.role, all='*')

        source, target = self.create_orgas(user=user)
        self.assertGET403(
            reverse('billing__create_related_invoice', args=(target.id,)),
        )

    def test_change_perm(self):
        "CHANGE creds are needed."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice],
        )
        self.add_credentials(user.role, all='!CHANGE')

        source, target = self.create_orgas(user=user)
        self.assertGET403(
            reverse('billing__create_related_invoice', args=(target.id,)),
        )


@skipIfCustomOrganisation
@skipIfCustomInvoice
class InvoiceEditionViewsTestCase(_BillingTestCase):
    def test_edition(self):
        user = self.login_as_root_and_get()
        SettingValue.objects.set_4_key(emitter_edition_key, True)

        name = 'Invoice001'
        invoice, source1, target1 = self.create_invoice_n_orgas(user=user, name=name)

        original_b_addr = invoice.billing_address
        self.assertIsInstance(original_b_addr, Address)

        original_s_addr = invoice.shipping_address
        self.assertIsInstance(original_s_addr, Address)

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

        create_address = Address.objects.create
        target2.billing_address = b_addr2 = create_address(
            name='Billing address #2', address='BA2 - Address',
            city='BA2 - City', country='BA2 - Country',
            owner=target2,
        )
        target2.shipping_address = s_addr2 = create_address(
            name='Shipping address #2', address='SA2 - Address',
            city='SA2 - City', country='SA2 - Country',
            owner=target2,
        )
        target2.save()

        currency = Currency.objects.all()[0]
        status = InvoiceStatus.objects.exclude(id=invoice.status_id)[0]
        response2 = self.client.post(
            url, follow=True,
            data={
                'user':            user.pk,
                'name':            name,
                'issuing_date':    self.formfield_value_date(2010,  9,  7),
                'expiration_date': self.formfield_value_date(2011, 11, 14),
                'status':          status.id,
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
        self.assertEqual(status, invoice.status)

        self.assertEqual(source2, invoice.source)
        self.assertEqual(target2, invoice.target)

        self.assertHaveRelation(subject=source2, type=REL_OBJ_BILL_ISSUED,   object=invoice)
        self.assertHaveRelation(subject=target2, type=REL_OBJ_BILL_RECEIVED, object=invoice)

        billing_address = invoice.billing_address
        self.assertIsInstance(billing_address, Address)
        self.assertEqual(invoice,         billing_address.owner)
        self.assertEqual(b_addr2.name,    billing_address.name)
        self.assertEqual(b_addr2.city,    billing_address.city)
        self.assertEqual(b_addr2.country, billing_address.country)

        shipping_address = invoice.shipping_address
        self.assertIsInstance(shipping_address, Address)
        self.assertEqual(invoice,            shipping_address.owner)
        self.assertEqual(s_addr2.name,       shipping_address.name)
        self.assertEqual(s_addr2.department, shipping_address.department)
        self.assertEqual(s_addr2.country,    shipping_address.country)

        # TODO: recycle instance instead?
        self.assertDoesNotExist(original_b_addr)
        self.assertDoesNotExist(original_s_addr)

    def test_edition__source_edition_forbidden(self):
        user = self.login_as_root_and_get()
        SettingValue.objects.set_4_key(emitter_edition_key, True)

        name = 'Invoice001'
        invoice, source1, target = self.create_invoice_n_orgas(
            user=user, name=name, number='INV-001',
        )

        url = invoice.get_edit_absolute_url()

        # Edition allowed (configuration) ---
        response1 = self.assertGET200(url)

        with self.assertNoException():
            source_f1 = response1.context['form'].fields[self.SOURCE_KEY]

        self.assertIsInstance(source_f1, CreatorEntityField)
        self.assertEqual(source1, source_f1.initial)

        # Edition forbidden ---
        SettingValue.objects.set_4_key(emitter_edition_key, False)

        response2 = self.assertGET200(url)

        with self.assertNoException():
            source_f2 = response2.context['form'].fields[self.SOURCE_KEY]

        self.assertIsInstance(source_f2, ReadonlyMessageField)
        self.assertEqual(
            _('Your configuration forbids you to edit the source Organisation'),
            source_f2.initial,
        )

        source2 = Organisation.objects.create(user=user, name='Source #2')
        name = f'{invoice.name} edited'
        self.assertNoFormError(self.client.post(
            url, follow=True,
            data={
                'user':     user.pk,
                'name':     name,
                'number':   invoice.number,
                'status':   invoice.status_id,
                'currency': invoice.currency_id,
                'discount': '0',

                self.SOURCE_KEY: source2.id,  # < == should not be used
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        ))

        invoice = self.refresh(invoice)
        self.assertEqual(name, invoice.name)
        self.assertEqual(source1, invoice.source)

        # Edition allowed (no number) ---
        invoice.number = ''
        invoice.save()

        response4 = self.assertGET200(url)

        with self.assertNoException():
            source_f4 = response4.context['form'].fields[self.SOURCE_KEY]

        self.assertIsInstance(source_f4, CreatorEntityField)

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_edition__user_change(self):
        "User changes => lines user changes."
        user = self.login_as_root_and_get()

        # Simpler to test with 2 superusers (do not have to create SetCredentials etc...)
        other_user = self.create_user()

        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Invoice001')
        self.assertEqual(user, invoice.user)

        create_pline = partial(
            ProductLine.objects.create, user=user, related_document=invoice,
        )
        create_sline = partial(
            ServiceLine.objects.create, user=user, related_document=invoice,
        )
        lines = [
            create_pline(on_the_fly_item='otf1',                      unit_price=Decimal('1')),
            create_pline(related_item=self.create_product(user=user), unit_price=Decimal('2')),
            create_sline(on_the_fly_item='otf2',                      unit_price=Decimal('4')),
            create_sline(related_item=self.create_service(user=user), unit_price=Decimal('5')),
        ]

        response = self.client.post(
            invoice.get_edit_absolute_url(), follow=True,
            data={
                'user':   other_user.pk,
                'name':   invoice.name,
                'status': invoice.status.id,

                'expiration_date': self.formfield_value_date(2011, 11, 14),

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

    def test_edition__discount_error(self):
        user = self.login_as_root_and_get()
        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Invoice001')
        url = invoice.get_edit_absolute_url()

        def post(discount):
            response = self.assertPOST200(
                url,
                follow=True,
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
            return self.get_form_or_fail(response)

        msg = _('Enter a number between 0 and 100 (it is a percentage).')
        self.assertFormError(post('150'), field='discount', errors=msg)
        self.assertFormError(post('-10'), field='discount', errors=msg)

    def test_edition__payment_info__no_one(self):
        user = self.login_as_root_and_get()

        source2 = Organisation.objects.create(user=user, name='Sega')
        invoice, source1, target = self.create_invoice_n_orgas(user=user, name='Playstations')

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
                'issuing_date':    self.formfield_value_date(2010,  9,  7),
                'expiration_date': self.formfield_value_date(2010, 10, 13),
                'status':          InvoiceStatus.objects.first().id,
                'currency':        currency.pk,
                'discount':        Decimal(),

                self.SOURCE_KEY: source2.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response)
        self.assertIsNone(self.refresh(invoice).payment_info)

    def test_edition__payment_info__one(self):
        "One PaymentInformation in the source => used automatically."
        user = self.login_as_root_and_get()

        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Invoice001')
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

    def test_edition__payment_info__several(self):
        "Several PaymentInformation in the source => default one is used."
        user = self.login_as_root_and_get()

        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Invoice001')

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
        self.assertEqual(pi2, invoice.payment_info)

    def test_edition__number(self):
        user = self.login_as_root_and_get()

        number = 'INV001'
        emitter, receiver = self.create_orgas(user=user)
        invoice = self.create_invoice(
            user=user, name='Invoice 001', number=number,
            source=emitter, target=receiver,
        )

        NumberGeneratorItem.objects.create(
            organisation=emitter,
            numbered_type=Invoice,
            is_edition_allowed=False,  # <==
            # data=...
        )

        url = invoice.get_edit_absolute_url()
        self.assertGET200(url)

        # POST (no change) ---
        data = {
            'user': user.pk,
            'name': invoice.name,
            'status': invoice.status_id,
            'currency': invoice.currency_id,
            'discount': '0',

            'number': invoice.number,

            # 'issuing_date':    self.formfield_value_date(2024,  9,  7),
            # 'expiration_date': self.formfield_value_date(2025, 11, 14),

            self.SOURCE_KEY: emitter.id,
            self.TARGET_KEY: self.formfield_value_generic_entity(receiver),
        }
        self.assertNoFormError(self.client.post(url, follow=True, data=data))
        self.assertEqual(number, self.refresh(invoice).number)

        # POST (change) ---
        response3 = self.assertPOST200(url, follow=True, data={**data, 'number': 'INV002'})
        self.assertFormError(
            self.get_form_or_fail(response3),
            field='number',
            errors=_('The number is set as not editable by the configuration.'),
        )

    def test_inner_edition(self):
        user = self.login_as_root_and_get()

        name = 'invoice001'
        invoice = self.create_invoice_n_orgas(user=user, name=name)[0]

        build_uri = partial(self.build_inneredit_uri, invoice)
        field_name = 'name'
        uri = build_uri(field_name)
        self.assertGET200(uri)

        name = name.title()
        response = self.client.post(uri, data={field_name: name})
        self.assertNoFormError(response)
        self.assertEqual(name, self.refresh(invoice).name)

        # Addresses should not be editable
        self.assertGET404(build_uri('billing_address'))
        self.assertGET404(build_uri('shipping_address'))

    def test_inner_edition__discount(self):
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        field_name = 'discount'
        uri = self.build_inneredit_uri(invoice, field_name)
        self.assertGET200(uri)

        response = self.assertPOST200(uri, data={field_name:  '110'})
        self.assertFormError(
            self.get_form_or_fail(response),
            field=field_name,
            errors=_('Enter a number between 0 and 100 (it is a percentage).'),
        )
