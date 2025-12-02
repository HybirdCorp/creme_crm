from datetime import date
from decimal import Decimal
from functools import partial

from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.template import Context, Template
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext as _

from creme.billing import bricks as billing_bricks
from creme.creme_core.forms import CreatorEntityField, ReadonlyMessageField
from creme.creme_core.gui import actions
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import (
    BrickDetailviewLocation,
    CremeEntity,
    Currency,
    FieldsConfig,
    Relation,
    RelationType,
    SettingValue,
    Vat,
)
from creme.creme_core.tests.base import (
    CremeTransactionTestCase,
    skipIfNotInstalled,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.creme_core.utils import currency_format
from creme.persons.constants import REL_SUB_CUSTOMER_SUPPLIER
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)
from creme.products.tests.base import skipIfCustomProduct

from ..actions import ExportInvoiceAction  # GenerateNumberAction
from ..constants import (
    REL_OBJ_BILL_ISSUED,
    REL_OBJ_BILL_RECEIVED,
    REL_SUB_BILL_ISSUED,
    REL_SUB_BILL_RECEIVED,
    UUID_INVOICE_STATUS_DRAFT,
    UUID_INVOICE_STATUS_TO_BE_SENT,
)
from ..models import (
    AdditionalInformation,
    InvoiceStatus,
    Line,
    PaymentInformation,
    PaymentTerms,
    SettlementTerms,
)
from ..setting_keys import emitter_edition_key
from .base import (
    Address,
    Contact,
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
class InvoiceTestCase(BrickTestCaseMixin, _BillingTestCase):
    def test_status__default(self):
        statuses = [*InvoiceStatus.objects.all()]
        self.assertEqual(8, len(statuses))

        default_status = self.get_alone_element(
            [status for status in statuses if status.is_default]
        )
        self.assertUUIDEqual(UUID_INVOICE_STATUS_DRAFT, default_status.uuid)

        # New default status => previous default status is updated
        new_status1 = InvoiceStatus.objects.create(name='OK', is_default=True)
        self.assertTrue(self.refresh(new_status1).is_default)
        self.assertEqual(9, InvoiceStatus.objects.count())
        self.assertFalse(
            InvoiceStatus.objects.exclude(id=new_status1.id).filter(is_default=True)
        )

        # No default status is found => new one is default one
        InvoiceStatus.objects.update(is_default=False)
        new_status2 = InvoiceStatus.objects.create(name='KO', is_default=False)
        self.assertTrue(self.refresh(new_status2).is_default)

    def test_status__validated(self):
        statuses = [*InvoiceStatus.objects.all()]
        self.assertEqual(8, len(statuses))

        validated_status = self.get_alone_element(
            [status for status in statuses if status.is_validated]
        )
        self.assertUUIDEqual(UUID_INVOICE_STATUS_TO_BE_SENT, validated_status.uuid)

        # New validated status => previous validated status is updated
        new_status1 = InvoiceStatus.objects.create(name='OK', is_validated=True)
        self.assertTrue(self.refresh(new_status1).is_validated)
        self.assertEqual(9, InvoiceStatus.objects.count())
        self.assertFalse(
            InvoiceStatus.objects.exclude(id=new_status1.id).filter(is_validated=True)
        )

        # No default status is found => new one is default one
        InvoiceStatus.objects.update(is_validated=False)
        new_status2 = InvoiceStatus.objects.create(name='KO', is_validated=False)
        self.assertTrue(self.refresh(new_status2).is_validated)

    def test_status__render(self):
        user = self.get_root_user()
        status = InvoiceStatus.objects.create(name='OK', color='00FF00')
        invoice = Invoice(user=user, name='OK Invoice', status=status)

        with self.assertNoException():
            render = Template(
                r'{% load creme_core_tags %}'
                r'{% print_field object=invoice field="status" tag=tag %}'
            ).render(Context({
                'user': user,
                'invoice': invoice,
                'tag': ViewTag.HTML_DETAIL,
            }))

        self.assertHTMLEqual(
            f'<div class="ui-creme-colored_status">'
            f' <div class="ui-creme-color_indicator" style="background-color:#{status.color};" />'
            f' <span>{status.name}</span>'
            f'</div>',
            render,
        )

    def test_source_n_target__creation(self):
        user = self.login_as_root_and_get()
        name = 'Invoice001'
        source, target = self.create_orgas(user=user)
        invoice = Invoice.objects.create(
            user=user,
            name=name,
            status=self.get_object_or_fail(InvoiceStatus, is_default=True),
            source=source,
            target=target,
        )
        self.assertEqual(user, invoice.user)
        self.assertEqual(name, invoice.name)
        self.assertTrue(invoice.status.is_default)

        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_ISSUED,   object=source)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_RECEIVED, object=target)

        with self.assertNumQueries(0):
            gotten_source = invoice.source

        with self.assertNumQueries(0):
            gotten_target = invoice.target

        self.assertEqual(source, gotten_source)
        self.assertEqual(target, gotten_target)

        # ---
        response = self.assertGET200(invoice.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=billing_bricks.TargetBrick,
        )
        self.assertInstanceLink(brick_node, source)
        self.assertInstanceLink(brick_node, target)

    def test_source_n_target__errors(self):
        "Errors at creation."
        user = self.get_root_user()
        source, target = self.create_orgas(user=user)

        build_invoice = partial(
            Invoice, user=user, name='Invoice001',
            status=self.get_object_or_fail(InvoiceStatus, is_default=True),
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

    def test_source_n_target__edition(self):
        user = self.get_root_user()
        name = 'Invoice001'
        source1, target1 = self.create_orgas(user=user)
        invoice = Invoice.objects.create(
            user=user,
            name=name,
            status=self.get_object_or_fail(InvoiceStatus, is_default=True),
            source=source1,
            target=target1,
        )
        source2, target2 = self.create_orgas(user=user, index=2)

        # ---
        invoice = self.refresh(invoice)

        invoice.source = source2
        invoice.save()

        self.assertHaveNoRelation(subject=invoice, type=REL_SUB_BILL_ISSUED, object=source1)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_ISSUED, object=source2)

        # ---
        invoice = self.refresh(invoice)

        invoice.target = target2
        invoice.save()

        self.assertHaveNoRelation(subject=invoice, type=REL_SUB_BILL_RECEIVED, object=target1)
        self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_RECEIVED, object=target2)

    def test_source_n_target__several_saves(self):
        "Several save without refreshing."
        user = self.get_root_user()
        name = 'invoice001'
        source1, target1 = self.create_orgas(user=user)
        invoice = Invoice.objects.create(
            user=user,
            name=name,
            status=self.get_object_or_fail(InvoiceStatus, is_default=True),
            source=source1,
            target=target1,
        )

        # ---
        source2, target2 = self.create_orgas(user=user, index=2)
        invoice.source = source2
        invoice.target = target2
        invoice.save()

        self.assertHaveNoRelation(invoice, REL_SUB_BILL_ISSUED, source1)
        self.assertHaveRelation(invoice, REL_SUB_BILL_ISSUED, source2)

        self.assertHaveNoRelation(invoice, REL_SUB_BILL_RECEIVED, target1)
        self.assertHaveRelation(invoice, REL_SUB_BILL_RECEIVED, target2)

        # ---
        source3, target3 = self.create_orgas(user=user, index=3)
        invoice.source = source3
        invoice.target = target3
        invoice.save()

        self.assertHaveNoRelation(invoice, REL_SUB_BILL_ISSUED, source2)
        self.assertHaveRelation(invoice, REL_SUB_BILL_ISSUED, source3)

        self.assertHaveNoRelation(invoice, REL_SUB_BILL_RECEIVED, target2)
        self.assertHaveRelation(invoice, REL_SUB_BILL_RECEIVED, target3)

    def test_detailview(self):
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
    def test_detailview__linked_opportunity(self):
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

    def test_detailview__generated_invoices(self):
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

    def test_create(self):
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
    def test_create__with_address(self):
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

        # ---
        detail_url = invoice.get_absolute_url()
        response1 = self.assertGET200(detail_url)
        pretty_brick_node = self.get_brick_node(
            self.get_html_tree(response1.content),
            brick=billing_bricks.BillingPrettyAddressBrick,
        )
        self.assertEqual(_('Addresses'), self.get_brick_title(pretty_brick_node))
        self.assertBrickHasAction(
            pretty_brick_node,
            url=f'{invoice.billing_address.get_edit_absolute_url()}?type=billing',
            action_type='edit',
        )
        self.assertBrickHasAction(
            pretty_brick_node,
            url=f'{invoice.shipping_address.get_edit_absolute_url()}?type=shipping',
            action_type='edit',
        )

        # ---
        BrickDetailviewLocation.objects.create_if_needed(
            brick=billing_bricks.BillingDetailedAddressBrick,
            order=600,
            zone=BrickDetailviewLocation.RIGHT,
            model=Invoice,
        )

        response2 = self.assertGET200(detail_url)
        detailed_brick_node = self.get_brick_node(
            self.get_html_tree(response2.content),
            brick=billing_bricks.BillingDetailedAddressBrick,
        )
        self.assertEqual(_('Addresses'), self.get_brick_title(detailed_brick_node))
        self.assertBrickHasAction(
            detailed_brick_node,
            url=f'{invoice.billing_address.get_edit_absolute_url()}?type=billing',
            action_type='edit',
        )
        self.assertBrickHasAction(
            detailed_brick_node,
            url=f'{invoice.shipping_address.get_edit_absolute_url()}?type=shipping',
            action_type='edit',
        )

    def test_create__contact_target(self):
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

    def test_create__error(self):
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

    def test_create__payment_info(self):
        "One PaymentInformation in the source => used automatically."
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        source = create_orga(name='Source Orga')
        target = create_orga(name='Target Orga')

        pi = PaymentInformation.objects.create(organisation=source, name='RIB 1')

        invoice = self.create_invoice(user=user, name='Invoice001', source=source, target=target)
        self.assertEqual(pi, invoice.payment_info)

    def test_create__payment_info__several(self):
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

    def test_create_related(self):
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

    def test_create_related__not_superuser(self):
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice],
        )
        self.add_credentials(user.role, all='*')

        source, target = self.create_orgas(user=user)
        self.assertGET200(
            reverse('billing__create_related_invoice', args=(target.id,)),
        )

    def test_create_related__creation_perm(self):
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

    def test_create_related__change_perm(self):
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

    def test_listview(self):
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

    def test_listview_export_actions(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice #1')[0]

        export_action = self.get_alone_element(
            action
            for action in actions.action_registry
                                 .instance_actions(user=user, instance=invoice)
            if isinstance(action, ExportInvoiceAction)
        )
        self.assertEqual('billing-export_invoice', export_action.id)
        self.assertEqual('redirect', export_action.type)
        self.assertEqual(
            reverse('billing__export', args=(invoice.id,)),
            export_action.url,
        )
        self.assertTrue(export_action.is_enabled)
        self.assertTrue(export_action.is_visible)

    def test_edit(self):
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

    def test_edit__source_edition_forbidden(self):
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
    def test_edit__user_change(self):
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

    def test_edit__discount_error(self):
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

    def test_edit__payment_info__no_one(self):
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

    def test_edit__payment_info__one(self):
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

    def test_edit__payment_info__several(self):
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

    def test_inner_edit(self):
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

    def test_inner_edit__discount(self):
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

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_get_lines(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
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
    def test_get_lines__cache(self):
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
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
        user = self.login_as_root_and_get()
        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]

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
        user = self.login_as_root_and_get()

        vat = self.get_object_or_fail(Vat, value='0.0')

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice001')[0]
        self.assertEqual(0, invoice._get_total_with_tax())

        kwargs = {'user': user, 'related_document': invoice, 'vat_value': vat}
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

        # ---
        response = self.assertGET200(invoice.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content), brick=billing_bricks.TotalBrick,
        )

        exc_total_node = self.get_html_node_or_fail(
            brick_node, './/h1[@name="total_no_vat"]'
        )
        self.assertIn(
            currency_format.currency(invoice.total_no_vat, invoice.currency),
            exc_total_node.text,
        )

        inc_total_node = self.get_html_node_or_fail(
            brick_node, './/h1[@name="total_vat"]'
        )
        self.assertIn(
            currency_format.currency(invoice.total_vat, invoice.currency),
            inc_total_node.text,
        )

    @skipIfCustomAddress
    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_clone(self):
        user = self.login_as_root_and_get()

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

        default_status = self.get_object_or_fail(InvoiceStatus, is_default=True)
        currency = Currency.objects.create(
            name='Martian dollar', local_symbol='M$',
            international_symbol='MUSD', is_custom=True,
        )
        invoice = self.create_invoice(
            user=user, name='Invoice001',
            source=source, target=target,
            currency=currency,
            status=InvoiceStatus.objects.filter(is_default=False).first(),
        )
        invoice.additional_info = AdditionalInformation.objects.all()[0]
        invoice.payment_terms = PaymentTerms.objects.all()[0]
        invoice.number = 'INV1235'
        invoice.save()

        kwargs = {'user': user, 'related_document': invoice}
        ServiceLine.objects.create(related_item=self.create_service(user=user), **kwargs)
        ServiceLine.objects.create(on_the_fly_item='otf service', **kwargs)
        ProductLine.objects.create(related_item=self.create_product(user=user), **kwargs)
        ProductLine.objects.create(on_the_fly_item='otf product', **kwargs)

        self.assertEqual(address_count + 2, Address.objects.count())

        origin_b_addr = invoice.billing_address
        origin_b_addr.zipcode += ' (edited)'
        origin_b_addr.save()

        origin_s_addr = invoice.shipping_address
        origin_s_addr.zipcode += ' (edited)'
        origin_s_addr.save()

        cloned = self.clone(invoice)

        self.assertNotEqual(invoice, cloned)  # Not the same pk
        self.assertEqual(invoice.name,   cloned.name)
        self.assertEqual(currency,       cloned.currency)
        self.assertEqual(default_status, cloned.status)
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

    # @skipIfCustomAddress
    # @skipIfCustomProductLine
    # @skipIfCustomServiceLine
    # def test_clone__method(self):  # DEPRECATED
    #     user = self.login_as_root_and_get()
    #
    #     create_orga = partial(Organisation.objects.create, user=user)
    #     source = create_orga(name='Source Orga')
    #     target = create_orga(name='Target Orga')
    #
    #     create_address = Address.objects.create
    #     target.billing_address = create_address(
    #         name='Billing address 01', address='BA1 - Address',
    #         po_box='BA1 - PO box', zipcode='BA1 - Zip code',
    #         city='BA1 - City', department='BA1 - Department',
    #         state='BA1 - State', country='BA1 - Country',
    #         owner=target,
    #     )
    #     target.shipping_address = create_address(
    #         name='Shipping address 01', address='SA1 - Address',
    #         po_box='SA1 - PO box', zipcode='SA1 - Zip code',
    #         city='SA1 - City', department='SA1 - Department',
    #         state='SA1 - State', country='SA1 - Country',
    #         owner=target,
    #     )
    #     target.save()
    #
    #     address_count = Address.objects.count()
    #
    #     default_status = self.get_object_or_fail(InvoiceStatus, is_default=True)
    #     currency = Currency.objects.create(
    #         name='Martian dollar', local_symbol='M$',
    #         international_symbol='MUSD', is_custom=True,
    #     )
    #     invoice = self.create_invoice(
    #         user=user, name='Invoice001',
    #         source=source, target=target,
    #         currency=currency,
    #         status=InvoiceStatus.objects.filter(is_default=False).first(),
    #     )
    #     invoice.additional_info = AdditionalInformation.objects.all()[0]
    #     invoice.payment_terms = PaymentTerms.objects.all()[0]
    #     invoice.save()
    #
    #     kwargs = {'user': user, 'related_document': invoice}
    #     ServiceLine.objects.create(related_item=self.create_service(user=user), **kwargs)
    #     ServiceLine.objects.create(on_the_fly_item='otf service', **kwargs)
    #     ProductLine.objects.create(related_item=self.create_product(user=user), **kwargs)
    #     ProductLine.objects.create(on_the_fly_item='otf product', **kwargs)
    #
    #     self.assertEqual(address_count + 2, Address.objects.count())
    #
    #     origin_b_addr = invoice.billing_address
    #     origin_b_addr.zipcode += ' (edited)'
    #     origin_b_addr.save()
    #
    #     origin_s_addr = invoice.shipping_address
    #     origin_s_addr.zipcode += ' (edited)'
    #     origin_s_addr.save()
    #
    #     cloned = self.refresh(invoice.clone())
    #     invoice = self.refresh(invoice)
    #
    #     self.assertNotEqual(invoice, cloned)  # Not the same pk
    #     self.assertEqual(invoice.name,   cloned.name)
    #     self.assertEqual(currency,       cloned.currency)
    #     self.assertEqual(default_status, cloned.status)
    #     self.assertIsNone(cloned.additional_info)  # Should not be cloned
    #     self.assertIsNone(cloned.payment_terms)    # Should not be cloned
    #     self.assertEqual(source, cloned.source)
    #     self.assertEqual(target, cloned.target)
    #     self.assertEqual('',     cloned.number)
    #
    #     # Lines are cloned
    #     src_line_ids = [line.id for line in invoice.iter_all_lines()]
    #     self.assertEqual(4, len(src_line_ids))
    #
    #     cloned_line_ids = [line.id for line in cloned.iter_all_lines()]
    #     self.assertEqual(4, len(cloned_line_ids))
    #
    #     self.assertFalse({*src_line_ids} & {*cloned_line_ids})
    #
    #     # Addresses are cloned
    #     self.assertEqual(address_count + 4, Address.objects.count())
    #
    #     billing_address = cloned.billing_address
    #     self.assertIsInstance(billing_address, Address)
    #     self.assertEqual(cloned,                billing_address.owner)
    #     self.assertEqual(origin_b_addr.name,    billing_address.name)
    #     self.assertEqual(origin_b_addr.city,    billing_address.city)
    #     self.assertEqual(origin_b_addr.zipcode, billing_address.zipcode)
    #
    #     shipping_address = cloned.shipping_address
    #     self.assertIsInstance(shipping_address, Address)
    #     self.assertEqual(cloned,                   shipping_address.owner)
    #     self.assertEqual(origin_s_addr.name,       shipping_address.name)
    #     self.assertEqual(origin_s_addr.department, shipping_address.department)
    #     self.assertEqual(origin_s_addr.zipcode,    shipping_address.zipcode)
    #
    # def test_clone__method__source_n_target(self):  # DEPRECATED
    #     "Internal relation-types should not be cloned."
    #     user = self.login_as_root_and_get()
    #
    #     invoice, source, target = self.create_invoice_n_orgas(user=user, name='Invoice001')
    #     cloned_source = source.clone()
    #     cloned_target = target.clone()
    #
    #     self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_ISSUED,   object=source)
    #     self.assertHaveRelation(subject=invoice, type=REL_SUB_BILL_RECEIVED, object=target)
    #     self.assertHaveNoRelation(invoice, type=REL_SUB_BILL_ISSUED,   object=cloned_source)
    #     self.assertHaveNoRelation(invoice, type=REL_SUB_BILL_RECEIVED, object=cloned_target)

    @skipIfCustomProductLine
    @skipIfCustomServiceLine
    def test_discounts(self):
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Invoice0001', discount=10)[0]

        kwargs = {'user': user, 'related_document': invoice}
        product_line = ProductLine.objects.create(
            on_the_fly_item='Flyyy product',
            unit_price=Decimal('1000.00'), quantity=2,
            discount=Decimal('10.00'),
            discount_unit=Line.Discount.PERCENT,
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
            discount_unit=Line.Discount.LINE_AMOUNT,
            vat_value=Vat.objects.default(),
            **kwargs
        )
        self.assertEqual(90, service_line.get_price_exclusive_of_tax())

        invoice = self.refresh(invoice)
        self.assertEqual(1710, invoice._get_total())  # total_exclusive_of_tax
        self.assertEqual(1710, invoice.total_no_vat)

    def test_delete(self):
        user = self.login_as_root_and_get()
        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Nerv')

        kwargs = {
            'user': user, 'related_document': invoice,
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

        url = invoice.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            invoice = self.refresh(invoice)

        self.assertIs(invoice.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(invoice)
        self.assertDoesNotExist(product_line)
        self.assertDoesNotExist(service_line)
        self.assertStillExists(source)
        self.assertStillExists(target)

    @skipIfCustomProduct
    def test_delete__linked_product(self):
        user = self.login_as_root_and_get()

        invoice = self.create_invoice_n_orgas(user=user, name='Nerv')[0]
        product = self.create_product(user=user, name='EVA')
        product_line = ProductLine.objects.create(
            # on_the_fly_item='Flyyy product',
            related_item=product,
            user=user,
            related_document=invoice,
            unit_price=Decimal('1000.00'),
            quantity=2,
            discount=Decimal('10.00'),
            discount_unit=Line.Discount.PERCENT,
            vat_value=Vat.objects.default(),
        )

        url = invoice.get_delete_absolute_url()
        self.assertPOST200(url, follow=True)

        with self.assertNoException():
            invoice = self.refresh(invoice)

        self.assertIs(invoice.is_deleted, True)

        self.assertPOST200(url, follow=True)
        self.assertDoesNotExist(invoice)
        self.assertDoesNotExist(product_line)

    def test_delete_status(self):
        user = self.login_as_root_and_get()

        new_status = InvoiceStatus.objects.first()
        status2del = InvoiceStatus.objects.create(name='OK')

        invoice = self.create_invoice_n_orgas(user=user, name='Nerv')[0]
        invoice.status = status2del
        invoice.save()

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='invoice_status',
            new_status=new_status,
            doc=invoice,
        )

    def test_delete_paymentterms(self):
        user = self.login_as_root_and_get()

        self.assertGET200(
            reverse('creme_config__model_portal', args=('billing', 'payment_terms')),
        )

        pterms = PaymentTerms.objects.create(name='3 months')

        invoice = self.create_invoice_n_orgas(user=user, name='Nerv')[0]
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
        user = self.login_as_root_and_get()

        currency = Currency.objects.create(
            name='Berry', local_symbol='B', international_symbol='BRY',
        )
        invoice = self.create_invoice_n_orgas(user=user, name='Nerv', currency=currency)[0]

        response = self.assertPOST200(reverse(
            'creme_config__delete_instance',
            args=('creme_core', 'currency', currency.id),
        ))
        self.assertFormError(
            self.get_form_or_fail(response),
            field='replace_billing__invoice_currency',
            errors=_('Deletion is not possible.'),
        )

        invoice = self.assertStillExists(invoice)
        self.assertEqual(currency, invoice.currency)

    def test_delete_additional_info(self):
        user = self.login_as_root_and_get()

        info = AdditionalInformation.objects.create(name='Agreement')
        invoice = self.create_invoice_n_orgas(user=user, name='Nerv')[0]
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
    def test_mass_import__no_total(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_no_total(
            user=user, model=Invoice, status_model=InvoiceStatus,
            # number_help_text=False,
            creation_number_help_text=False,
        )

    def test_mass_import__total_no_vat_n_vat(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_total_no_vat_n_vat(
            user=user, model=Invoice, status_model=InvoiceStatus,
        )

    @skipIfCustomAddress
    def test_mass_import__update__target_has_address(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_update(
            user=user,
            model=Invoice, status_model=InvoiceStatus,
            target_billing_address=True,
        )

    @skipIfCustomAddress
    def test_mass_import__update__target_has_no_address(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_update(
            user=user,
            model=Invoice, status_model=InvoiceStatus,
            target_billing_address=False,
        )

    @skipIfCustomAddress
    def test_mass_import__update_total__no_total(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_no_total(
            user=user,
            model=Invoice, status_model=InvoiceStatus,
            update=True,
            creation_number_help_text=False,
        )

    def test_mass_import__update_total__error(self):
        user = self.login_as_root_and_get()
        doc = self._build_csv_doc([('Bill #1', 'Nerv', 'Acme', '300', '15')], user=user)
        response = self.assertPOST200(
            self._build_import_url(Invoice),
            follow=True,
            data={
                'step':     1,
                'document': doc.id,
                # has_header

                'user': user.id,
                'key_fields': ['name'],

                'name_colselect':   1,
                'number_colselect': 0,

                'issuing_date_colselect':    0,
                'expiration_date_colselect': 0,

                'status_colselect': 0,
                'status_defval':    InvoiceStatus.objects.all()[0].pk,

                'discount_colselect': 0,
                'discount_defval':    '0',

                'currency_colselect': 0,
                'currency_defval':    Currency.objects.all()[0].pk,

                'acceptation_date_colselect': 0,

                'comment_colselect':         0,
                'additional_info_colselect': 0,
                'payment_terms_colselect':   0,
                'payment_type_colselect':    0,

                'description_colselect':         0,
                'buyers_order_number_colselect': 0,  # Invoice only...

                'source_persons_organisation_colselect': 2,
                'target_persons_organisation_colselect': 3,
                'target_persons_contact_colselect': 0,

                'totals_mode': '2',  # Compute total with VAT
                'totals_total_no_vat_colselect': 4,
                'totals_vat_colselect': 5,

                # 'property_types',
                # 'fixed_relations',
                # 'dyn_relations',
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='totals',
            errors=_('You cannot compute totals in update mode.'),
        )

    def test_mass_import__emitter_edition(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_update__emitter_edition(
            user=user, model=Invoice, emitter_edition_ok=False,
        )

    def test_mass_import__emitter_edition__error(self):
        SettingValue.objects.set_4_key(emitter_edition_key, True)

        user = self.login_as_root_and_get()
        self._aux_test_csv_import_update__emitter_edition(
            user=user, model=Invoice, emitter_edition_ok=True,
        )

    def test_ReceivedInvoicesBrick(self):
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user=user)

        response1 = self.assertGET200(target.get_absolute_url())
        brick_node1 = self.get_brick_node(
            self.get_html_tree(response1.content),
            brick=billing_bricks.ReceivedInvoicesBrick,
        )
        self.assertEqual(_('Received invoices'), self.get_brick_title(brick_node1))

        # ---
        invoice = Invoice.objects.create(
            user=user, name='My Invoice',
            status=InvoiceStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
            number='INV123',
        )

        # ----
        response2 = self.assertGET200(target.get_absolute_url())
        brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content),
            brick=billing_bricks.ReceivedInvoicesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node2,
            count=1,
            title='{count} Received invoice',
            plural_title='{count} Received invoices',
        )
        self.assertListEqual(
            [
                _('Name'), _('Number'), _('Expiration date'), _('Status'),
                _('Total without VAT'), _('Action'),
            ],
            self.get_brick_table_column_titles(brick_node2),
        )
        rows = self.get_brick_table_rows(brick_node2)
        table_cells = self.get_alone_element(rows).findall('.//td')
        self.assertEqual(6, len(table_cells))
        self.assertInstanceLink(table_cells[0], entity=invoice)
        self.assertEqual(invoice.number, table_cells[1].text)
        self.assertEqual(
            date_format(invoice.expiration_date, 'DATE_FORMAT'),
            table_cells[2].text,
        )
        self.assertEqual(invoice.status.name, table_cells[3].text)
        # TODO: test table_cells[4]

        # ----
        context = self.build_context(user=user, instance=target)
        # Queries:
        #   - FieldsConfig
        #   - COUNT Invoices
        #   - BrickStates
        #   - SettingValues "is open"/"how empty fields"
        #   - Invoices
        #   - SettingValues "creme_core-display_currency_local_symbol"
        with self.assertNumQueries(6):
            render = billing_bricks.ReceivedInvoicesBrick().detailview_display(context)

        brick_node3 = self.get_brick_node(
            self.get_html_tree(render), brick=billing_bricks.ReceivedInvoicesBrick,
        )
        self.assertInstanceLink(brick_node3, entity=invoice)

    def test_ReceivedInvoicesBrick__hidden_expiration(self):
        "Field 'expiration_date' is hidden."
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user=user)

        FieldsConfig.objects.create(
            content_type=Invoice,
            descriptions=[
                ('expiration_date',  {FieldsConfig.HIDDEN: True}),
            ],
        )

        Invoice.objects.create(
            user=user, name='My Quote',
            status=InvoiceStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
        )

        response = self.assertGET200(target.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.ReceivedInvoicesBrick,
        )
        self.assertListEqual(
            [_('Name'), _('Number'), _('Status'), _('Total without VAT'), _('Action')],
            self.get_brick_table_column_titles(brick_node),
        )
        rows = self.get_brick_table_rows(brick_node)
        row = self.get_alone_element(rows)
        self.assertEqual(5, len(row.findall('.//td')))

    @override_settings(HIDDEN_VALUE='?')
    def test_ReceivedInvoicesBrick__forbidden(self):
        "No VIEW permission."
        user = self.login_as_standard(allowed_apps=['persons', 'billing'])
        self.add_credentials(user.role, own='*')

        source, target = self.create_orgas(user=user)

        Invoice.objects.create(
            user=self.get_root_user(), name='My Quote',
            status=InvoiceStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
        )

        response = self.assertGET200(target.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.ReceivedInvoicesBrick,
        )
        rows = self.get_brick_table_rows(brick_node)
        table_cells = self.get_alone_element(rows).findall('.//td')
        self.assertEqual(6, len(table_cells))
        self.assertEqual('?', table_cells[0].text)
        self.assertEqual('?', table_cells[1].text)
        self.assertEqual('?', table_cells[2].text)
        self.assertEqual('?', table_cells[3].text)
        self.assertEqual('?', table_cells[4].text)
        self.assertIsNone(table_cells[5].text)


@skipIfCustomOrganisation
@skipIfCustomInvoice
@skipIfCustomProductLine
@skipIfCustomServiceLine
class BillingDeleteTestCase(_BillingTestCaseMixin, CremeTransactionTestCase):
    def setUp(self):  # setUpClass does not work here
        super().setUp()
        self.populate('creme_core', 'creme_config', 'billing')
        self.user = self.login_as_root_and_get()

        # NB: we need pk=1 for the default instances created by formset for detail-view.
        #     It would not be useful if we reset ID sequences...
        Vat.objects.get_or_create(id=1, value=Decimal('0.0'))

    def test_delete01(self):
        user = self.user
        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Invoice001')
        product_line = ProductLine.objects.create(
            user=user,
            related_document=invoice,
            on_the_fly_item='My product',
        )
        service_line = ServiceLine.objects.create(
            user=user,
            related_document=invoice,
            on_the_fly_item='My service',
        )

        b_addr = invoice.billing_address
        self.assertIsInstance(b_addr, Address)

        s_addr = invoice.billing_address
        self.assertIsInstance(s_addr, Address)

        self.refresh(invoice).delete()
        self.assertDoesNotExist(invoice)
        self.assertDoesNotExist(product_line)
        self.assertDoesNotExist(service_line)

        self.assertStillExists(source)
        self.assertStillExists(target)

        self.assertDoesNotExist(b_addr)
        self.assertDoesNotExist(s_addr)

    def test_delete02(self):
        "Can't be deleted."
        user = self.user
        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Invoice001')
        service_line = ServiceLine.objects.create(
            user=user, related_document=invoice, on_the_fly_item='Flyyyyy',
        )
        rel1 = Relation.objects.get(
            subject_entity=invoice.id, object_entity=service_line.id,
        )

        # This relation prohibits the deletion of the invoice
        ce = CremeEntity.objects.create(user=user)
        rtype = RelationType.objects.builder(
            id='test-subject_linked', predicate='is linked to',
            is_internal=True,
        ).symmetric(id='test-object_linked', predicate='is linked to').get_or_create()[0]
        rel2 = Relation.objects.create(
            subject_entity=invoice, object_entity=ce, type=rtype, user=user,
        )

        self.assertRaises(ProtectedError, self.refresh(invoice).delete)

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
