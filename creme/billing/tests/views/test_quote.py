from datetime import date
from decimal import Decimal

from django.contrib.contenttypes.models import ContentType
from django.forms import CharField
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.billing import bricks as billing_bricks
from creme.billing.constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
from creme.billing.custom_forms import QUOTE_CREATION_CFORM
from creme.billing.forms.base import BillingSourceSubCell, BillingTargetSubCell
from creme.billing.models import (
    NumberGeneratorItem,
    QuoteStatus,
    SettlementTerms,
)
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.forms import CreatorEntityField
from creme.creme_core.gui.custom_form import FieldGroupList
from creme.creme_core.models import Currency, CustomFormConfigItem, Relation
from creme.creme_core.tests.base import skipIfNotInstalled
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.constants import REL_SUB_PROSPECT
from creme.persons.tests.base import skipIfCustomOrganisation

from ..base import (
    Contact,
    Invoice,
    Organisation,
    Quote,
    SalesOrder,
    _BillingTestCase,
    skipIfCustomQuote,
)


@skipIfCustomOrganisation
@skipIfCustomQuote
class QuoteDetailViewTestCase(BrickTestCaseMixin, _BillingTestCase):
    def test_main(self):
        user = self.login_as_root_and_get()

        status = QuoteStatus.objects.filter(won=False)[0]
        quote, emitter, receiver = self.create_quote_n_orgas(
            user=user, name='My Quote', status=status,
        )
        url = quote.get_absolute_url()
        response1 = self.assertGET200(url)
        self.assertTemplateUsed(response1, 'billing/view_quote.html')

        tree1 = self.get_html_tree(response1.content)
        self.assertConvertButtons(
            tree1,
            [
                {'title': _('Convert to Salesorder'), 'type': 'sales_order', 'disabled': False},
                {'title': _('Convert to Invoice'),    'type': 'invoice',     'disabled': False},
            ],
        )

        self.get_brick_node(tree1, brick=billing_bricks.ProductLinesBrick)
        self.get_brick_node(tree1, brick=billing_bricks.ServiceLinesBrick)
        self.get_brick_node(tree1, brick=billing_bricks.TargetBrick)
        self.get_brick_node(tree1, brick=billing_bricks.TotalBrick)

        hat_brick_node1 = self.get_brick_node(
            tree1, brick=billing_bricks.QuoteCardHatBrick,
        )
        self.assertInstanceLink(hat_brick_node1, entity=emitter)
        self.assertInstanceLink(hat_brick_node1, entity=receiver)

        indicator_path = (
            './/div[@class="business-card-indicator business-card-warning-indicator"]'
        )
        self.assertIsNone(hat_brick_node1.find(indicator_path))

        # Expiration passed ---
        quote.status = QuoteStatus.objects.filter(won=True)[0]
        quote.save()
        response2 = self.assertGET200(url)
        hat_brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content),
            brick=billing_bricks.QuoteCardHatBrick,
        )
        indicator_node = self.get_html_node_or_fail(hat_brick_node2, indicator_path)
        self.assertEqual(_('Expiration date passed'), indicator_node.text.strip())

    def test_generated_invoices(self):
        user = self.login_as_root_and_get()

        quote = self.create_quote_n_orgas(user=user, name='Quote 001')[0]

        self._convert(200, quote, 'invoice')
        invoice = self.get_alone_element(Invoice.objects.all())

        response = self.assertGET200(quote.get_absolute_url())
        hat_brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.QuoteCardHatBrick,
        )
        self.assertInstanceLink(hat_brick_node, entity=invoice)

    def test_salesorder_creation_forbidden(self):
        "Cannot create Sales Orders => convert button disabled."
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Organisation, Quote, Invoice],  # Not SalesOrder
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        quote = self.create_quote_n_orgas(user=user, name='My Quote 0001')[0]
        response = self.assertGET200(quote.get_absolute_url())
        self.assertConvertButtons(
            self.get_html_tree(response.content),
            [
                {'title': _('Convert to Salesorder'), 'disabled': True},
                {'title': _('Convert to Invoice'),    'type': 'invoice', 'disabled': False},
            ],
        )

    def test_invoice_creation_forbidden(self):
        "Cannot create Invoice => convert button disabled."
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Organisation, Quote, SalesOrder],  # Not Invoice
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        quote = self.create_quote_n_orgas(user=user, name='Quote #0001')[0]
        response = self.assertGET200(quote.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/view_quote.html')
        self.assertConvertButtons(
            self.get_html_tree(response.content),
            [
                {'title': _('Convert to Salesorder'), 'type': 'sales_order', 'disabled': False},
                {'title': _('Convert to Invoice'), 'disabled': True},
            ],
        )

    @skipIfNotInstalled('creme.opportunities')
    def test_linked_opportunity(self):
        from creme.opportunities import get_opportunity_model
        from creme.opportunities.constants import REL_SUB_LINKED_QUOTE
        from creme.opportunities.models import SalesPhase

        user = self.login_as_root_and_get()
        quote, emitter, receiver = self.create_quote_n_orgas(
            user=user, name='My quote 0001',
        )
        opp = get_opportunity_model().objects.create(
            user=user, name='Linked opp',
            sales_phase=SalesPhase.objects.all()[0],
            emitter=emitter, target=receiver,
        )

        Relation.objects.create(
            subject_entity=quote,
            type_id=REL_SUB_LINKED_QUOTE,
            object_entity=opp,
            user=user,
        )

        response = self.assertGET200(quote.get_absolute_url())
        hat_brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=billing_bricks.QuoteCardHatBrick,
        )
        self.assertInstanceLink(hat_brick_node, entity=opp)


@skipIfCustomOrganisation
@skipIfCustomQuote
class QuoteCreationTestCase(_BillingTestCase):
    @override_settings(SOFTWARE_LABEL='My CRM')
    def test_source_not_managed(self):
        "Source is not managed + no number given."
        user = self.login_as_root_and_get()

        managed_orga = self.get_alone_element(Organisation.objects.filter_managed_by_creme())
        response1 = self.assertGET200(reverse('billing__create_quote'))
        default_status = self.get_object_or_fail(QuoteStatus, is_default=True)

        with self.assertNoException():
            form = response1.context['form']
            fields = form.fields
            source_f = fields[self.SOURCE_KEY]
            number_f = fields['number']
            status_f = fields['status']

        self.assertEqual(managed_orga, source_f.initial)
        self.assertFalse(number_f.required)
        self.assertEqual(
            _(
                'If you chose an organisation managed by {software} (like «{organisation}») '
                'as source organisation, a number will be automatically generated.'
            ).format(software='My CRM', organisation=managed_orga),
            number_f.help_text,
        )
        self.assertEqual(default_status.id, status_f.get_bound_field(form, 'status').initial)

        # ---
        terms = SettlementTerms.objects.all()[0]
        quote, source, target = self.create_quote_n_orgas(
            user=user, name='My Quote', payment_type=terms.id,
        )

        self.assertEqual(date(year=2012, month=4, day=22), quote.expiration_date)
        self.assertIsNone(quote.acceptation_date)
        # self.assertEqual('0',   quote.number)
        self.assertEqual('',    quote.number)
        self.assertEqual(terms, quote.payment_type)

        self.assertHaveRelation(subject=quote,  type=REL_SUB_BILL_ISSUED,   object=source)
        self.assertHaveRelation(subject=quote,  type=REL_SUB_BILL_RECEIVED, object=target)
        # NB: workflow
        self.assertHaveRelation(subject=target, type=REL_SUB_PROSPECT,      object=source)

        # ---
        quote2, source2, target2 = self.create_quote_n_orgas(user=user, name='My Quote Two')
        self.assertHaveRelation(subject=target2, type=REL_SUB_PROSPECT, object=source2)

    def test_source_managed(self):
        "Source is managed + no number given + other default status."
        user = self.login_as_root_and_get()
        status = QuoteStatus.objects.create(name='OK', is_default=True)

        response1 = self.assertGET200(reverse('billing__create_quote'))
        form = response1.context['form']
        self.assertEqual(status.id, form.fields['status'].get_bound_field(form, 'status').initial)

        # ---
        source, target1 = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=source,
            numbered_type=ContentType.objects.get_for_model(Quote),
        )
        item.data['format'] = 'QUO-{counter:04}'
        item.save()

        quote = self.create_quote(user=user, name='My Quote', source=source, target=target1)

        self.assertEqual(date(year=2012, month=4, day=22), quote.expiration_date)
        self.assertIsNone(quote.acceptation_date)
        self.assertStartsWith('QUO-0001', quote.number)
        self.assertIsNone(quote.payment_type)

        self.assertHaveRelation(subject=quote,   type=REL_SUB_BILL_ISSUED,   object=source)
        self.assertHaveRelation(subject=quote,   type=REL_SUB_BILL_RECEIVED, object=target1)
        self.assertHaveRelation(subject=target1, type=REL_SUB_PROSPECT,      object=source)

        # ---
        target2 = Organisation.objects.create(user=user, name='Target #2')
        quote2 = self.create_quote(
            user=user, name='My second Quote', source=source, target=target2,
        )

        self.assertHaveRelation(subject=target2, type=REL_SUB_PROSPECT, object=source)
        self.assertEqual('QUO-0002', quote2.number)

    def test_contact_target(self):
        "Workflow for Contact too."
        user = self.login_as_root_and_get()

        orga = Organisation.objects.create(user=user, name='Acme')
        contact = Contact.objects.create(user=user, first_name='John', last_name='Doe')
        quote = self.create_quote(
            user=user, name='My Quote', source=orga, target=contact,
        )

        self.assertHaveRelation(subject=quote, type=REL_SUB_BILL_ISSUED,   object=orga)
        self.assertHaveRelation(subject=quote, type=REL_SUB_BILL_RECEIVED, object=contact)
        # NB: workflow
        self.assertHaveRelation(subject=contact, type=REL_SUB_PROSPECT, object=orga)

    def test_no_number_field(self):
        "The field 'number' is not in the form."
        self.login_as_root()

        cfci = CustomFormConfigItem.objects.get(
            descriptor_id=QUOTE_CREATION_CFORM.id,
            role=None,
            superuser=False,
        )
        cfci.store_groups(FieldGroupList.from_cells(
            model=Quote,
            data=[
                {
                    'name': _('General information'),
                    'cells': [
                        (EntityCellRegularField, {'name': 'user'}),
                        (EntityCellRegularField, {'name': 'name'}),
                        (EntityCellRegularField, {'name': 'discount'}),
                        (EntityCellRegularField, {'name': 'currency'}),
                        (EntityCellRegularField, {'name': 'status'}),

                        BillingSourceSubCell(model=Quote).into_cell(),
                        BillingTargetSubCell(model=Quote).into_cell(),
                    ],
                },
            ],
            cell_registry=QUOTE_CREATION_CFORM.build_cell_registry(),
            allowed_extra_group_classes=(*QUOTE_CREATION_CFORM.extra_group_classes,)
        ))
        cfci.save()

        response = self.assertGET200(reverse('billing__create_quote'))

        with self.assertNoException():
            fields = response.context['form'].fields

        self.assertNotIn('number', fields)

    def test_no_default_status(self):
        self.login_as_root()
        QuoteStatus.objects.update(is_default=False)

        response = self.assertGET200(reverse('billing__create_quote'))
        self.assertIsNone(self.get_form_or_fail(response).initial.get('status'))

    def test_number__managed_emitter__number_edition_allowed(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        number = 'QU#0001'
        invoice = self.create_quote(
            user=user, name='Quote001', source=source, target=target,
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
            numbered_type=ContentType.objects.get_for_model(Quote),
        )
        self.assertTrue(item.is_edition_allowed)

        item.data['format'] = 'QUO-{counter:04}'
        item.is_edition_allowed = False
        item.save()

        # Error ---
        name = 'Quote001'
        currency = Currency.objects.all()[0]
        response = self.client.post(
            reverse('billing__create_quote'),
            follow=True,
            data={
                'user': user.pk,
                'name': name,
                'status': QuoteStatus.objects.first().id,

                'currency': currency.id,
                'discount': '0',

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),

                'number': 'Q010',  # <====
            },
        )
        self.assertFormError(
            self.get_form_or_fail(response),
            field='number',
            errors=_('The number is set as not editable by the configuration.'),
        )

        # OK ---
        quote = self.create_quote(
            user=user, name=name, source=source, target=target, currency=currency,
        )
        self.assertEqual('QUO-0001', quote.number)


@skipIfCustomOrganisation
@skipIfCustomQuote
class QuoteRelatedCreationTestCase(_BillingTestCase):
    def test_main(self):
        user = self.login_as_root_and_get()
        default_status = self.get_object_or_fail(QuoteStatus, is_default=True)

        source, target = self.create_orgas(user=user)
        url = reverse('billing__create_related_quote', args=(target.id,))
        response1 = self.assertGET200(url)

        context = response1.context
        self.assertEqual(
            _('Create a quote for «{entity}»').format(entity=target),
            context.get('title'),
        )
        self.assertEqual(Quote.save_label, context.get('submit_label'))

        with self.assertNoException():
            form = context['form']
            status_f = form.fields['status']

        self.assertDictEqual({self.TARGET_KEY: target}, form.initial)
        self.assertEqual(default_status.id, status_f.get_bound_field(form, 'status').initial)

        # ---
        name = 'Quote#1'
        currency = Currency.objects.all()[0]
        status = QuoteStatus.objects.all()[1]
        response2 = self.client.post(
            url, follow=True,
            data={
                'user':            user.pk,
                'name':            name,
                'issuing_date':    self.formfield_value_date(2013, 12, 14),
                'expiration_date': self.formfield_value_date(2014, 1,  21),
                'status':          status.id,
                'currency':        currency.id,
                'discount':        Decimal(),

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),

            },
        )
        self.assertNoFormError(response2)

        quote = self.get_object_or_fail(Quote, name=name)
        self.assertEqual(date(year=2013, month=12, day=14), quote.issuing_date)
        self.assertEqual(date(year=2014, month=1,  day=21), quote.expiration_date)
        self.assertEqual(currency, quote.currency)
        self.assertEqual(status,   quote.status)

        self.assertHaveRelation(subject=quote, type=REL_SUB_BILL_ISSUED,   object=source)
        self.assertHaveRelation(subject=quote, type=REL_SUB_BILL_RECEIVED, object=target)

    def test_regular_user(self):
        "Not a super-user + other default status."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Quote],
        )
        self.add_credentials(user.role, all='*')

        status = QuoteStatus.objects.create(name='OK', is_default=True)
        source, target = self.create_orgas(user=user)
        response = self.assertGET200(
            reverse('billing__create_related_quote', args=(target.id,)),
        )
        form = self.get_form_or_fail(response)
        self.assertEqual(status.id, form.fields['status'].get_bound_field(form, 'status').initial)

    def test_creation_credentials(self):
        "Creation creds are needed."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            # creatable_models=[Quote],
        )
        self.add_credentials(user.role, all='*')

        source, target = self.create_orgas(user=user)
        self.assertGET403(
            reverse('billing__create_related_quote', args=(target.id,)),
        )

    def test_modification_credentials(self):
        "CHANGE creds are needed."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Quote],
        )
        self.add_credentials(user.role, all='!CHANGE')

        source, target = self.create_orgas(user=user)
        self.assertGET403(
            reverse('billing__create_related_quote', args=(target.id,)),
        )

    def test_no_default_status(self):
        user = self.login_as_root_and_get()
        QuoteStatus.objects.update(is_default=False)

        source, target = self.create_orgas(user=user)
        response = self.assertGET200(
            reverse('billing__create_related_quote', args=(target.id,)),
        )
        self.assertIsNone(self.get_form_or_fail(response).initial.get('status'))


@skipIfCustomOrganisation
@skipIfCustomQuote
class QuoteEditionTestCase(_BillingTestCase):
    def test_main(self):
        user = self.login_as_root_and_get()

        name = 'my quote'
        quote, source, target = self.create_quote_n_orgas(user=user, name=name)

        url = quote.get_edit_absolute_url()
        response1 = self.assertGET200(url)

        with self.assertNoException():
            number_f = response1.context['form'].fields['number']

        self.assertFalse(number_f.help_text)

        name = name.title()
        currency = Currency.objects.create(
            name='Martian dollar', local_symbol='M$',
            international_symbol='MUSD', is_custom=True,
        )
        status = QuoteStatus.objects.all()[1]
        response2 = self.client.post(
            url, follow=True,
            data={
                'user': user.pk,
                'name': name,

                'issuing_date':     self.formfield_value_date(2012, 2, 12),
                'expiration_date':  self.formfield_value_date(2012, 3, 14),
                'acceptation_date': self.formfield_value_date(2012, 3, 13),

                'status': status.id,

                'currency': currency.id,
                'discount': Decimal(),

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response2)

        quote = self.refresh(quote)
        self.assertEqual(name,                             quote.name)
        self.assertEqual(date(year=2012, month=2, day=12), quote.issuing_date)
        self.assertEqual(date(year=2012, month=3, day=14), quote.expiration_date)
        self.assertEqual(date(year=2012, month=3, day=13), quote.acceptation_date)
        self.assertEqual(currency,                         quote.currency)
        self.assertEqual(status,                           quote.status)

        self.assertHaveRelation(subject=quote, type=REL_SUB_BILL_ISSUED,   object=source)
        self.assertHaveRelation(subject=quote, type=REL_SUB_BILL_RECEIVED, object=target)

    def test_change_related_organisations(self):
        "Change source/target + perms."
        user = self.login_as_standard(
            allowed_apps=('persons', 'billing'),
            creatable_models=[Quote],
        )
        self.add_credentials(user.role, all=['VIEW'], own='*')

        quote, source1, target1 = self.create_quote_n_orgas(user=user, name='My quote')

        unlinkable_source, unlinkable_target = self.create_orgas(user=self.get_root_user())
        self.assertFalse(user.has_perm_to_link(unlinkable_source))
        self.assertFalse(user.has_perm_to_link(unlinkable_target))

        def post(source, target):
            return self.client.post(
                quote.get_edit_absolute_url(), follow=True,
                data={
                    'user':       user.pk,
                    'name':       quote.name,
                    'status':     quote.status_id,
                    'currency':   quote.currency_id,
                    'discount':   quote.discount,

                    self.SOURCE_KEY: source.id,
                    self.TARGET_KEY: self.formfield_value_generic_entity(target),
                },
            )

        response = post(unlinkable_source, unlinkable_target)
        self.assertEqual(200, response.status_code)

        form = self.get_form_or_fail(response)
        msg_fmt = _('You are not allowed to link this entity: {}').format
        self.assertFormError(form, field=self.SOURCE_KEY, errors=msg_fmt(unlinkable_source))
        self.assertFormError(form, field=self.TARGET_KEY, errors=msg_fmt(unlinkable_target))

        # ----
        source2, target2 = self.create_orgas(user=user)
        self.assertNoFormError(post(source2, target2))

        self.assertHaveRelation(subject=quote, type=REL_SUB_BILL_ISSUED,   object=source2)
        self.assertHaveRelation(subject=quote, type=REL_SUB_BILL_RECEIVED, object=target2)

        self.assertHaveNoRelation(subject=quote, type=REL_SUB_BILL_ISSUED,   object=source1)
        self.assertHaveNoRelation(subject=quote, type=REL_SUB_BILL_RECEIVED, object=target1)

    def test_not_linkable_organisations(self):
        "Change source/target + perms: not linkable but not changed."
        user = self.login_as_standard(
            allowed_apps=('persons', 'billing'),
            creatable_models=[Quote],
        )
        self.add_credentials(user.role, all=['VIEW'], own='*')

        quote, source, target = self.create_quote_n_orgas(user=user, name='My quote')

        source.user = target.user = self.get_root_user()
        source.save()
        target.save()
        self.assertFalse(user.has_perm_to_link(source))
        self.assertFalse(user.has_perm_to_link(target))

        status = QuoteStatus.objects.exclude(id=quote.status_id).first()
        response = self.client.post(
            quote.get_edit_absolute_url(), follow=True,
            data={
                'user':     user.pk,
                'name':     quote.name,
                'status':   status.id,
                'currency': quote.currency_id,
                'discount': quote.discount,

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),
            },
        )
        self.assertNoFormError(response)
        self.assertEqual(status, self.refresh(quote).status)
        self.assertHaveRelation(subject=quote, type=REL_SUB_BILL_ISSUED,   object=source)
        self.assertHaveRelation(subject=quote, type=REL_SUB_BILL_RECEIVED, object=target)

    def test_emitter_edition_forbidden(self):
        "SettingValue is ignored."
        user = self.login_as_root_and_get()

        quote, source, target = self.create_quote_n_orgas(
            user=user, name='Quote #01', number='Q-001',
        )
        response = self.assertGET200(quote.get_edit_absolute_url())

        with self.assertNoException():
            source_f = response.context['form'].fields[self.SOURCE_KEY]

        self.assertIsInstance(source_f, CreatorEntityField)
        self.assertEqual(source, source_f.initial)


@skipIfCustomOrganisation
@skipIfCustomQuote
class QuoteInnerEditionTestCase(_BillingTestCase):
    def test_number__allowed__emitter_is_managed(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        item = self.get_object_or_fail(
            NumberGeneratorItem,
            organisation=source,
            numbered_type=ContentType.objects.get_for_model(Quote),
        )
        self.assertTrue(item.is_edition_allowed)

        quote = self.create_quote(user=user, name='Order001', source=source, target=target)
        self.assertStartsWith(quote.number, _('QUO'))

        field_name = 'number'
        uri = self.build_inneredit_uri(quote, field_name)
        response1 = self.assertGET200(uri)
        form_field_name = f'override-{field_name}'

        with self.assertNoException():
            number_f = response1.context['form'].fields[form_field_name]

        self.assertIsInstance(number_f, CharField)
        self.assertEqual(quote.number, number_f.initial)

        # POST ---
        number = 'Q1256'
        self.assertNoFormError(self.client.post(uri, data={form_field_name: number}))
        self.assertEqual(number, self.refresh(quote).number)

    def test_number__allowed__emitter_is_not_managed(self):
        user = self.login_as_root_and_get()

        quote, source, __target = self.create_quote_n_orgas(user=user, name='Order001')
        self.assertFalse(quote.number)
        self.assertFalse(NumberGeneratorItem.objects.filter(
            organisation=source, numbered_type=quote.entity_type,
        ))

        field_name = 'number'
        uri = self.build_inneredit_uri(quote, field_name)
        response1 = self.assertGET200(uri)
        form_field_name = f'override-{field_name}'

        with self.assertNoException():
            number_f = response1.context['form'].fields[form_field_name]

        self.assertIsInstance(number_f, CharField)

        # POST ---
        number = 'QU125'
        self.assertNoFormError(self.client.post(uri, data={form_field_name: number}))
        self.assertEqual(number, self.refresh(quote).number)

    def test_number__forbidden(self):
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        NumberGeneratorItem.objects.filter(
            organisation=source,
            numbered_type=ContentType.objects.get_for_model(Quote),
        ).update(is_edition_allowed=False)

        quote = self.create_quote(user=user, name='Order001', source=source, target=target)
        old_number = quote.number
        self.assertStartsWith(old_number, _('QUO'))

        field_name = 'number'
        uri = self.build_inneredit_uri(quote, field_name)

        self.assertContains(
            self.client.get(uri),
            _('The number is set as not editable by the configuration.'),
            html=True,
        )

        # POST ---
        form_field_name = f'override-{field_name}'
        response2 = self.assertPOST200(uri, data={form_field_name: 'Q1256'})
        self.assertFormError(
            self.get_form_or_fail(response2),
            field=form_field_name,
            errors=_('The number is set as not editable by the configuration.'),
        )
        self.assertEqual(old_number, self.refresh(quote).number)


@skipIfCustomOrganisation
@skipIfCustomQuote
class QuoteListviewTestCase(_BillingTestCase):
    def test_main(self):
        user = self.login_as_root_and_get()

        quote1 = self.create_quote_n_orgas(user=user, name='Quote1')[0]
        quote2 = self.create_quote_n_orgas(user=user, name='Quote2')[0]

        response = self.assertGET200(Quote.get_lv_absolute_url())

        with self.assertNoException():
            quotes_page = response.context['page_obj']

        self.assertEqual(2, quotes_page.paginator.count)
        self.assertCountEqual([quote1, quote2], quotes_page.paginator.object_list)
