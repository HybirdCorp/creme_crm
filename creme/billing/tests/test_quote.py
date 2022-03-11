# -*- coding: utf-8 -*-

from datetime import date
from decimal import Decimal
from functools import partial

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.translation import gettext as _

from creme.creme_core.auth import EntityCredentials
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui import actions
from creme.creme_core.gui.custom_form import FieldGroupList
from creme.creme_core.models import (
    Currency,
    CustomFormConfigItem,
    SetCredentials,
)
from creme.persons.constants import REL_SUB_PROSPECT
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

from ..actions import ExportQuoteAction
from ..constants import REL_SUB_BILL_ISSUED, REL_SUB_BILL_RECEIVED
from ..custom_forms import QUOTE_CREATION_CFORM
from ..forms.base import BillingSourceSubCell, BillingTargetSubCell
from ..models import QuoteStatus, SettlementTerms, SimpleBillingAlgo
from .base import (
    Address,
    Invoice,
    Organisation,
    Quote,
    SalesOrder,
    ServiceLine,
    _BillingTestCase,
    skipIfCustomQuote,
    skipIfCustomServiceLine,
)


@skipIfCustomOrganisation
@skipIfCustomQuote
class QuoteTestCase(_BillingTestCase):
    def test_detailview01(self):
        "Cannot create Sales Orders => convert button disabled."
        self.login(
            is_superuser=False,
            allowed_apps=['billing', 'persons'],
            creatable_models=[Organisation, Quote, Invoice],  # Not SalesOrder
        )
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_OWN,
        )

        quote = self.create_quote_n_orgas('My Quote')[0]
        response = self.assertGET200(quote.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/view_quote.html')
        self.assertConvertButtons(
            response,
            [
                {'title': _('Convert to Salesorder'), 'type': 'sales_order', 'disabled': True},
                {'title': _('Convert to Invoice'),    'type': 'invoice',     'disabled': False},
            ],
        )

    def test_detailview02(self):
        "Cannot create Invoice => convert button disabled."
        self.login(
            is_superuser=False,
            allowed_apps=['billing', 'persons'],
            creatable_models=[Organisation, Quote, SalesOrder],  # Not Invoice
        )
        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_OWN
        )

        quote = self.create_quote_n_orgas('My Quote')[0]
        response = self.assertGET200(quote.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/view_quote.html')
        self.assertConvertButtons(
            response,
            [
                {'title': _('Convert to Salesorder'), 'type': 'sales_order', 'disabled': False},
                {'title': _('Convert to Invoice'),    'type': 'invoice',     'disabled': True},
            ],
        )

    def test_createview01(self):
        "Source is not managed + no number given."
        self.login()

        managed_orgas = [*Organisation.objects.filter_managed_by_creme()]
        self.assertEqual(1, len(managed_orgas))

        managed_orga = managed_orgas[0]
        response = self.assertGET200(reverse('billing__create_quote'))

        with self.assertNoException():
            fields = response.context['form'].fields
            source_f = fields[self.SOURCE_KEY]
            number_f = fields['number']

        self.assertEqual(managed_orga, source_f.initial)
        self.assertFalse(number_f.required)
        self.assertEqual(
            _(
                'If you chose an organisation managed by Creme (like «{}») '
                'as source organisation, a number will be automatically generated.'
            ).format(managed_orga),
            number_f.help_text,
        )

        # ---
        terms = SettlementTerms.objects.all()[0]
        quote, source, target = self.create_quote_n_orgas('My Quote', payment_type=terms.id)

        self.assertEqual(date(year=2012, month=4, day=22), quote.expiration_date)
        self.assertIsNone(quote.acceptation_date)
        self.assertEqual('0',   quote.number)
        self.assertEqual(terms, quote.payment_type)

        self.assertRelationCount(1, quote,  REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, quote,  REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, target, REL_SUB_PROSPECT,      source)

        # ---
        quote2, source2, target2 = self.create_quote_n_orgas('My Quote Two')
        self.assertRelationCount(1, target2, REL_SUB_PROSPECT, source2)

    def test_createview02(self):
        "Source is managed + no number given."
        user = self.login()
        self.assertGET200(reverse('billing__create_quote'))

        source, target1 = self.create_orgas()
        self._set_managed(source)

        algo_qs = SimpleBillingAlgo.objects.filter(
            organisation=source.id,
            ct=ContentType.objects.get_for_model(Quote),
        )
        self.assertEqual([0], [*algo_qs.values_list('last_number', flat=True)])

        quote = self.create_quote('My Quote', source=source, target=target1)

        self.assertEqual(date(year=2012, month=4, day=22), quote.expiration_date)
        self.assertIsNone(quote.acceptation_date)
        self.assertEqual('DE1', quote.number)
        self.assertIsNone(quote.payment_type)

        self.assertRelationCount(1, quote,  REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, quote,  REL_SUB_BILL_RECEIVED, target1)
        self.assertRelationCount(1, target1, REL_SUB_PROSPECT,     source)

        self.assertEqual([1], [*algo_qs.values_list('last_number', flat=True)])

        # ---
        target2 = Organisation.objects.create(user=user, name='Target #2')
        quote2 = self.create_quote('My second Quote', source, target2)

        self.assertRelationCount(1, target2, REL_SUB_PROSPECT, source)
        self.assertEqual('DE2', quote2.number)

    def test_createview03(self):
        "Source is not managed + a number is given."
        self.login()

        number = 'Q123'
        quote, source, target = self.create_quote_n_orgas('My Quote', number=number)
        self.assertEqual(number, quote.number)

    def test_createview04(self):
        "The field 'number' is not in the form."
        self.login()

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

    def test_create_related01(self):
        user = self.login()

        source, target = self.create_orgas()
        url = reverse('billing__create_related_quote', args=(target.id,))
        response = self.assertGET200(url)

        context = response.context
        self.assertEqual(
            _('Create a quote for «{entity}»').format(entity=target),
            context.get('title'),
        )
        self.assertEqual(Quote.save_label, context.get('submit_label'))

        # ---
        with self.assertNoException():
            form = response.context['form']

        self.assertDictEqual(
            {
                'status': 1,
                # 'target': target,  # deprecated
                self.TARGET_KEY: target,
            },
            form.initial,
        )

        name = 'Quote#1'
        currency = Currency.objects.all()[0]
        status = QuoteStatus.objects.all()[1]
        response = self.client.post(
            url, follow=True,
            data={
                'user':            user.pk,
                'name':            name,
                'issuing_date':    '2013-12-14',
                'expiration_date': '2014-1-21',
                'status':          status.id,
                'currency':        currency.id,
                'discount':        Decimal(),

                self.SOURCE_KEY: source.id,
                self.TARGET_KEY: self.formfield_value_generic_entity(target),

            },
        )
        self.assertNoFormError(response)

        quote = self.get_object_or_fail(Quote, name=name)
        self.assertEqual(date(year=2013, month=12, day=14), quote.issuing_date)
        self.assertEqual(date(year=2014, month=1,  day=21), quote.expiration_date)
        self.assertEqual(currency, quote.currency)
        self.assertEqual(status,   quote.status)

        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target)

    def test_create_related02(self):
        "Not a super-user."
        self.login(
            is_superuser=False,
            allowed_apps=['persons', 'billing'],
            creatable_models=[Quote],
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
            reverse('billing__create_related_quote', args=(target.id,)),
        )

    def test_create_related03(self):
        "Creation creds are needed."
        self.login(
            is_superuser=False,
            allowed_apps=['persons', 'billing'],
            # creatable_models=[Quote],
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
            reverse('billing__create_related_quote', args=(target.id,)),
        )

    def test_create_related04(self):
        "CHANGE creds are needed."
        self.login(
            is_superuser=False,
            allowed_apps=['persons', 'billing'],
            creatable_models=[Quote],
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
            reverse('billing__create_related_quote', args=(target.id,)),
        )

    def test_editview01(self):
        user = self.login()

        name = 'my quote'
        quote, source, target = self.create_quote_n_orgas(name)

        url = quote.get_edit_absolute_url()
        response1 = self.assertGET200(url)

        with self.assertNoException():
            number_f = response1.context['form'].fields['number']

        self.assertFalse(number_f.help_text)

        name = name.title()
        currency = Currency.objects.create(
            name='Marsian dollar', local_symbol='M$',
            international_symbol='MUSD', is_custom=True,
        )
        status = QuoteStatus.objects.all()[1]
        response2 = self.client.post(
            url, follow=True,
            data={
                'user': user.pk,
                'name': name,

                'issuing_date':     '2012-2-12',
                'expiration_date':  '2012-3-14',
                'acceptation_date': '2012-3-13',

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

        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target)

    def test_editview02(self):
        "Change source/target + perms."
        user = self.login(
            is_superuser=False,
            allowed_apps=('persons', 'billing'),
            creatable_models=[Quote],
        )

        create_sc = partial(SetCredentials.objects.create, role=self.role)
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
        create_sc(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        quote, source1, target1 = self.create_quote_n_orgas('My quote')

        unlinkable_source, unlinkable_target = self.create_orgas(user=self.other_user)
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
        msg_fmt = _('You are not allowed to link this entity: {}').format
        self.assertFormError(response, 'form', self.SOURCE_KEY, msg_fmt(unlinkable_source))
        self.assertFormError(response, 'form', self.TARGET_KEY, msg_fmt(unlinkable_target))

        # ----
        source2, target2 = self.create_orgas(user=user)
        self.assertNoFormError(post(source2, target2))

        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   source2)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target2)

        self.assertRelationCount(0, quote, REL_SUB_BILL_ISSUED,   source1)
        self.assertRelationCount(0, quote, REL_SUB_BILL_RECEIVED, target1)

    def test_editview03(self):
        "Change source/target + perms: unlinkable but not changed."
        user = self.login(
            is_superuser=False,
            allowed_apps=('persons', 'billing'),
            creatable_models=[Quote],
        )

        create_sc = partial(SetCredentials.objects.create, role=self.role)
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
        create_sc(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)

        quote, source, target = self.create_quote_n_orgas('My quote')

        source.user = target.user = self.other_user
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
        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target)

    def test_listview(self):
        self.login()

        quote1 = self.create_quote_n_orgas('Quote1')[0]
        quote2 = self.create_quote_n_orgas('Quote2')[0]

        response = self.assertGET200(Quote.get_lv_absolute_url())

        with self.assertNoException():
            quotes_page = response.context['page_obj']

        self.assertEqual(2, quotes_page.paginator.count)
        self.assertSetEqual({quote1, quote2}, {*quotes_page.paginator.object_list})

    def test_listview_actions(self):
        user = self.login()
        quote = self.create_quote_n_orgas('Quote #1')[0]

        export_actions = [
            action
            for action in actions.actions_registry
                                 .instance_actions(user=user, instance=quote)
            if isinstance(action, ExportQuoteAction)
        ]
        self.assertEqual(1, len(export_actions))

        export_action = export_actions[0]
        self.assertEqual('billing-export_quote', export_action.id)
        self.assertEqual('redirect', export_action.type)
        self.assertEqual(reverse('billing__export', args=(quote.id,)), export_action.url)
        self.assertTrue(export_action.is_enabled)
        self.assertTrue(export_action.is_visible)

    # def test_delete_status01(self):
    def test_delete_status(self):
        self.login()
        new_status = QuoteStatus.objects.first()
        status2del = QuoteStatus.objects.create(name='OK')

        quote = self.create_quote_n_orgas('Nerv', status=status2del)[0]

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='quote_status',
            new_status=new_status,
            doc=quote,
        )

    @skipIfCustomAddress
    def test_mass_import01(self):
        self.login()
        self._aux_test_csv_import(Quote, QuoteStatus)

    def test_mass_import02(self):
        "Source is managed."
        user = self.login()

        count = Quote.objects.count()
        create_orga = partial(Organisation.objects.create, user=user)

        source = create_orga(name='Nerv')
        self._set_managed(source)

        target1 = create_orga(name='Acme')
        target2 = create_orga(name='NHK')

        lines_count = 2
        names = [f'Billdoc #{i:04}' for i in range(1, lines_count + 1)]
        numbers = [f'INV{i:04}' for i in range(1, lines_count + 1)]  # Should not be used
        lines = [
            (names[0], numbers[0], source.name, target1.name),
            (names[1], numbers[1], source.name, target2.name),
        ]

        doc = self._build_csv_doc(lines)
        url = self._build_import_url(Quote)
        self.assertGET200(url)

        def_status = QuoteStatus.objects.all()[0]
        def_currency = Currency.objects.all()[0]
        response = self.assertPOST200(
            url,
            follow=True,
            data={
                'step':     1,
                'document': doc.id,
                # has_header

                'user': self.user.id,
                'key_fields': [],

                'name_colselect':   1,
                'number_colselect': 2,

                'issuing_date_colselect':    0,
                'expiration_date_colselect': 0,

                'status_colselect': 0,
                'status_defval':    def_status.pk,

                'discount_colselect': 0,
                'discount_defval':    '0',

                'currency_colselect': 0,
                'currency_defval':    def_currency.pk,

                'acceptation_date_colselect': 0,

                'comment_colselect':         0,
                'additional_info_colselect': 0,
                'payment_terms_colselect':   0,
                'payment_type_colselect':    0,

                'description_colselect':         0,
                'buyers_order_number_colselect': 0,  # Invoice only...

                'source_persons_organisation_colselect': 3,
                'source_persons_organisation_create':    False,

                'target_persons_organisation_colselect': 4,
                'target_persons_organisation_create':    False,

                'target_persons_contact_colselect': 0,
                'target_persons_contact_create':    False,

                # 'property_types',
                # 'fixed_relations',
                # 'dyn_relations',
            },
        )

        self.assertNoFormError(response)

        self._execute_job(response)
        self.assertEqual(count + len(lines), Quote.objects.count())

        quote1 = self.get_object_or_fail(Quote, name=names[0])
        self.assertEqual(source, quote1.source)
        self.assertEqual(target1, quote1.target)
        number1 = quote1.number
        self.assertStartsWith(number1, settings.QUOTE_NUMBER_PREFIX)

        quote2 = self.get_object_or_fail(Quote, name=names[1])
        self.assertEqual(source, quote2.source)
        self.assertEqual(target2, quote2.target)
        number2 = quote2.number
        self.assertStartsWith(number2, settings.QUOTE_NUMBER_PREFIX)

        self.assertNotEqual(number1, number2)

    @skipIfCustomAddress
    @skipIfCustomServiceLine
    def test_clone01(self):
        "Organisation not managed => number is set to '0'."
        user = self.login()
        source, target = self.create_orgas(user=user)

        target.billing_address = b_addr = Address.objects.create(
            name='Billing address 01',
            address='BA1 - Address', city='BA1 - City',
            owner=target,
        )
        target.save()

        # status = QuoteStatus.objects.filter(is_default=False)[0] TODO

        quote = self.create_quote(
            'Quote001', source, target,
            # status=status,
            number='12',
        )
        quote.acceptation_date = date.today()
        quote.save()

        sl = ServiceLine.objects.create(
            related_item=self.create_service(), user=user, related_document=quote,
        )

        cloned = self.refresh(quote.clone())
        quote = self.refresh(quote)

        self.assertIsNone(cloned.acceptation_date)
        # self.assertTrue(cloned.status.is_default) TODO
        self.assertEqual('0', cloned.number)

        self.assertNotEqual(quote, cloned)  # Not the same pk
        self.assertEqual(source, cloned.source)
        self.assertEqual(target, cloned.target)

        # Lines are cloned
        cloned_lines = [*cloned.iter_all_lines()]
        self.assertEqual(1, len(cloned_lines))
        self.assertNotEqual([sl], cloned_lines)

        # Addresses are cloned
        billing_address = cloned.billing_address
        self.assertIsInstance(billing_address, Address)
        self.assertEqual(cloned,      billing_address.owner)
        self.assertEqual(b_addr.name, billing_address.name)
        self.assertEqual(b_addr.city, billing_address.city)

    def test_clone02(self):
        "Organisation is managed => number is generated (but only once BUGFIX)."
        self.login()

        source, target = self.create_orgas()
        self._set_managed(source)

        quote = self.create_quote('My Quote', source=source, target=target)
        self.assertEqual('DE1', quote.number)

        cloned = quote.clone()
        self.assertEqual('DE2', cloned.number)

    def test_num_queries(self):
        """Avoid the queries about line sa creation
        (because these queries can be really slow with a lot of entities)
        """
        from django.db import DEFAULT_DB_ALIAS, connections
        from django.test.utils import CaptureQueriesContext

        user = self.login()

        # NB: we do not use assertNumQueries, because external
        #     signal handlers can add their owns queries
        context = CaptureQueriesContext(connections[DEFAULT_DB_ALIAS])

        status = QuoteStatus.objects.all()[0]
        source, target = self.create_orgas(user=user)

        with context:
            quote = Quote.objects.create(
                user=user, name='My Quote', status=status,
                source=source, target=target,
            )

        self.assertTrue(quote.pk)
        self.assertEqual(0, quote.total_no_vat)
        self.assertEqual(0, quote.total_vat)

        for query_info in context.captured_queries:
            query = query_info['sql']
            self.assertNotIn('billing_productline', query)
            self.assertNotIn('billing_serviceline', query)
