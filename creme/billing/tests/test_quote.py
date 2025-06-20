from datetime import date
from decimal import Decimal
from functools import partial

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.translation import gettext as _

# from creme.creme_core.auth import EntityCredentials
from creme.creme_core.core.entity_cell import EntityCellRegularField
from creme.creme_core.gui import actions
from creme.creme_core.gui.custom_form import FieldGroupList
from creme.creme_core.gui.view_tag import ViewTag
# from creme.creme_core.models import SetCredentials
from creme.creme_core.models import (
    Currency,
    CustomFormConfigItem,
    FieldsConfig,
)
from creme.creme_core.tests.views.base import BrickTestCaseMixin
from creme.persons.constants import REL_SUB_PROSPECT
from creme.persons.tests.base import (
    skipIfCustomAddress,
    skipIfCustomOrganisation,
)

from ..actions import ExportQuoteAction
from ..bricks import ReceivedQuotesBrick
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
class QuoteTestCase(BrickTestCaseMixin, _BillingTestCase):
    def test_status(self):
        statuses = [*QuoteStatus.objects.all()]
        self.assertEqual(4, len(statuses))

        default_status = self.get_alone_element(
            [status for status in statuses if status.is_default]
        )
        self.assertEqual(1, default_status.pk)

        # New default status => previous default status is updated
        new_status1 = QuoteStatus.objects.create(name='OK', is_default=True)
        self.assertTrue(self.refresh(new_status1).is_default)
        self.assertEqual(5, QuoteStatus.objects.count())
        self.assertFalse(
            QuoteStatus.objects.exclude(id=new_status1.id).filter(is_default=True)
        )

        # No default status is found => new one is default one
        QuoteStatus.objects.update(is_default=False)
        new_status2 = QuoteStatus.objects.create(name='KO', is_default=False)
        self.assertTrue(self.refresh(new_status2).is_default)

    def test_status_render(self):
        user = self.get_root_user()
        status = QuoteStatus.objects.create(name='OK', color='00FF00')
        ctxt = {
            'user': user,
            'quote': Quote(user=user, name='OK Quote', status=status),
        }
        template = Template(
            r'{% load creme_core_tags %}'
            r'{% print_field object=quote field="status" tag=tag %}'
        )
        self.assertEqual(
            status.name,
            template.render(Context({**ctxt, 'tag': ViewTag.TEXT_PLAIN})).strip(),
        )
        self.assertHTMLEqual(
            f'<div class="ui-creme-colored_status">'
            f' <div class="ui-creme-color_indicator" style="background-color:#{status.color};" />'
            f' <span>{status.name}</span>'
            f'</div>',
            template.render(Context({**ctxt, 'tag': ViewTag.HTML_DETAIL})),
        )

    def test_detailview01(self):
        "Cannot create Sales Orders => convert button disabled."
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Organisation, Quote, Invoice],  # Not SalesOrder
        )
        # SetCredentials.objects.create(
        #     role=user.role,
        #     value=EntityCredentials.VIEW | EntityCredentials.LINK,
        #     set_type=SetCredentials.ESET_OWN,
        # )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]
        response = self.assertGET200(quote.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/view_quote.html')
        self.assertConvertButtons(
            response,
            [
                # {'title': _('Convert to Salesorder'), 'type': 'sales_order', 'disabled': True},
                {'title': _('Convert to Salesorder'), 'disabled': True},
                {'title': _('Convert to Invoice'),    'type': 'invoice',     'disabled': False},
            ],
        )

    def test_detailview02(self):
        "Cannot create Invoice => convert button disabled."
        user = self.login_as_standard(
            allowed_apps=['billing', 'persons'],
            creatable_models=[Organisation, Quote, SalesOrder],  # Not Invoice
        )
        # SetCredentials.objects.create(
        #     role=user.role,
        #     value=EntityCredentials.VIEW | EntityCredentials.LINK,
        #     set_type=SetCredentials.ESET_OWN
        # )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        quote = self.create_quote_n_orgas(user=user, name='My Quote')[0]
        response = self.assertGET200(quote.get_absolute_url())
        self.assertTemplateUsed(response, 'billing/view_quote.html')
        self.assertConvertButtons(
            response,
            [
                {'title': _('Convert to Salesorder'), 'type': 'sales_order', 'disabled': False},
                {'title': _('Convert to Invoice'), 'disabled': True},
            ],
        )

    @override_settings(SOFTWARE_LABEL='My CRM')
    def test_createview01(self):
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
        # self.assertEqual(default_status.id, form.initial.get('status'))
        self.assertEqual(default_status.id, status_f.get_bound_field(form, 'status').initial)

        # ---
        terms = SettlementTerms.objects.all()[0]
        quote, source, target = self.create_quote_n_orgas(
            user=user, name='My Quote', payment_type=terms.id,
        )

        self.assertEqual(date(year=2012, month=4, day=22), quote.expiration_date)
        self.assertIsNone(quote.acceptation_date)
        self.assertEqual('0',   quote.number)
        self.assertEqual(terms, quote.payment_type)

        self.assertRelationCount(1, quote,  REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, quote,  REL_SUB_BILL_RECEIVED, target)
        self.assertRelationCount(1, target, REL_SUB_PROSPECT,      source)

        # ---
        quote2, source2, target2 = self.create_quote_n_orgas(user=user, name='My Quote Two')
        self.assertRelationCount(1, target2, REL_SUB_PROSPECT, source2)

    def test_createview02(self):
        "Source is managed + no number given + other default status."
        user = self.login_as_root_and_get()
        status = QuoteStatus.objects.create(name='OK', is_default=True)

        response1 = self.assertGET200(reverse('billing__create_quote'))
        # self.assertEqual(status.id, response1.context['form'].initial.get('status'))
        form = response1.context['form']
        self.assertEqual(status.id, form.fields['status'].get_bound_field(form, 'status').initial)

        # ---
        source, target1 = self.create_orgas(user=user)
        self._set_managed(source)

        algo_qs = SimpleBillingAlgo.objects.filter(
            organisation=source.id,
            ct=ContentType.objects.get_for_model(Quote),
        )
        self.assertEqual([0], [*algo_qs.values_list('last_number', flat=True)])

        quote = self.create_quote(user=user, name='My Quote', source=source, target=target1)

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
        quote2 = self.create_quote(
            user=user, name='My second Quote', source=source, target=target2,
        )

        self.assertRelationCount(1, target2, REL_SUB_PROSPECT, source)
        self.assertEqual('DE2', quote2.number)

    def test_createview03(self):
        "Source is not managed + a number is given."
        user = self.login_as_root_and_get()

        number = 'Q123'
        quote, source, target = self.create_quote_n_orgas(
            user=user, name='My Quote', number=number,
        )
        self.assertEqual(number, quote.number)

    def test_createview04(self):
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

    def test_createview__no_default_status(self):
        self.login_as_root()
        QuoteStatus.objects.update(is_default=False)

        response = self.assertGET200(reverse('billing__create_quote'))
        self.assertIsNone(response.context['form'].initial.get('status'))

    def test_create_related01(self):
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

        self.assertDictEqual(
            {
                # 'status': 1,
                'status': default_status.id,
                self.TARGET_KEY: target,
            },
            form.initial,
        )

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

        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target)

    def test_create_related02(self):
        "Not a super-user + other default status."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Quote],
        )
        # SetCredentials.objects.create(
        #     role=user.role,
        #     value=(
        #         EntityCredentials.VIEW
        #         | EntityCredentials.CHANGE
        #         | EntityCredentials.DELETE
        #         | EntityCredentials.LINK
        #         | EntityCredentials.UNLINK
        #     ),
        #     set_type=SetCredentials.ESET_ALL,
        # )
        self.add_credentials(user.role, all='*')

        status = QuoteStatus.objects.create(name='OK', is_default=True)
        source, target = self.create_orgas(user=user)
        response = self.assertGET200(
            reverse('billing__create_related_quote', args=(target.id,)),
        )
        # self.assertEqual(status.id, response.context['form'].initial.get('status'))
        form = response.context['form']
        self.assertEqual(status.id, form.fields['status'].get_bound_field(form, 'status').initial)

    def test_create_related__creation_credentials(self):
        "Creation creds are needed."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            # creatable_models=[Quote],
        )
        # SetCredentials.objects.create(
        #     role=user.role,
        #     value=(
        #         EntityCredentials.VIEW
        #         | EntityCredentials.CHANGE
        #         | EntityCredentials.DELETE
        #         | EntityCredentials.LINK
        #         | EntityCredentials.UNLINK
        #     ),
        #     set_type=SetCredentials.ESET_ALL,
        # )
        self.add_credentials(user.role, all='*')

        source, target = self.create_orgas(user=user)
        self.assertGET403(
            reverse('billing__create_related_quote', args=(target.id,)),
        )

    def test_create_related__modification_credentials(self):
        "CHANGE creds are needed."
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Quote],
        )
        # SetCredentials.objects.create(
        #     role=user.role,
        #     value=(
        #         EntityCredentials.VIEW
        #         # | EntityCredentials.CHANGE
        #         | EntityCredentials.DELETE
        #         | EntityCredentials.LINK
        #         | EntityCredentials.UNLINK
        #     ),
        #     set_type=SetCredentials.ESET_ALL,
        # )
        self.add_credentials(user.role, all='!CHANGE')

        source, target = self.create_orgas(user=user)
        self.assertGET403(
            reverse('billing__create_related_quote', args=(target.id,)),
        )

    def test_createview_related__no_default_status(self):
        user = self.login_as_root_and_get()
        QuoteStatus.objects.update(is_default=False)

        source, target = self.create_orgas(user=user)
        response = self.assertGET200(
            reverse('billing__create_related_quote', args=(target.id,)),
        )
        self.assertIsNone(response.context['form'].initial.get('status'))

    def test_editview01(self):
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
            name='Marsian dollar', local_symbol='M$',
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

        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target)

    def test_editview02(self):
        "Change source/target + perms."
        user = self.login_as_standard(
            allowed_apps=('persons', 'billing'),
            creatable_models=[Quote],
        )
        # create_sc = partial(SetCredentials.objects.create, role=user.role)
        # create_sc(
        #     value=(
        #         EntityCredentials.VIEW
        #         | EntityCredentials.CHANGE
        #         | EntityCredentials.DELETE
        #         | EntityCredentials.LINK
        #         | EntityCredentials.UNLINK
        #     ),
        #     set_type=SetCredentials.ESET_OWN,
        # )
        # create_sc(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)
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

        form = response.context['form']
        msg_fmt = _('You are not allowed to link this entity: {}').format
        self.assertFormError(form, field=self.SOURCE_KEY, errors=msg_fmt(unlinkable_source))
        self.assertFormError(form, field=self.TARGET_KEY, errors=msg_fmt(unlinkable_target))

        # ----
        source2, target2 = self.create_orgas(user=user)
        self.assertNoFormError(post(source2, target2))

        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   source2)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target2)

        self.assertRelationCount(0, quote, REL_SUB_BILL_ISSUED,   source1)
        self.assertRelationCount(0, quote, REL_SUB_BILL_RECEIVED, target1)

    def test_editview03(self):
        "Change source/target + perms: unlinkable but not changed."
        user = self.login_as_standard(
            allowed_apps=('persons', 'billing'),
            creatable_models=[Quote],
        )
        # create_sc = partial(SetCredentials.objects.create, role=user.role)
        # create_sc(
        #     value=(
        #         EntityCredentials.VIEW
        #         | EntityCredentials.CHANGE
        #         | EntityCredentials.DELETE
        #         | EntityCredentials.LINK
        #         | EntityCredentials.UNLINK
        #     ),
        #     set_type=SetCredentials.ESET_OWN,
        # )
        # create_sc(value=EntityCredentials.VIEW, set_type=SetCredentials.ESET_ALL)
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
        self.assertRelationCount(1, quote, REL_SUB_BILL_ISSUED,   source)
        self.assertRelationCount(1, quote, REL_SUB_BILL_RECEIVED, target)

    def test_listview(self):
        user = self.login_as_root_and_get()

        quote1 = self.create_quote_n_orgas(user=user, name='Quote1')[0]
        quote2 = self.create_quote_n_orgas(user=user, name='Quote2')[0]

        response = self.assertGET200(Quote.get_lv_absolute_url())

        with self.assertNoException():
            quotes_page = response.context['page_obj']

        self.assertEqual(2, quotes_page.paginator.count)
        self.assertCountEqual([quote1, quote2], quotes_page.paginator.object_list)

    def test_listview_actions(self):
        user = self.login_as_root_and_get()
        quote = self.create_quote_n_orgas(user=user, name='Quote #1')[0]

        export_action = self.get_alone_element(
            action
            for action in actions.actions_registry
                                 .instance_actions(user=user, instance=quote)
            if isinstance(action, ExportQuoteAction)
        )
        self.assertEqual('billing-export_quote', export_action.id)
        self.assertEqual('redirect', export_action.type)
        self.assertEqual(reverse('billing__export', args=(quote.id,)), export_action.url)
        self.assertTrue(export_action.is_enabled)
        self.assertTrue(export_action.is_visible)

    def test_delete_status(self):
        user = self.login_as_root_and_get()
        new_status = QuoteStatus.objects.first()
        status2del = QuoteStatus.objects.create(name='OK')

        quote = self.create_quote_n_orgas(user=user, name='Nerv', status=status2del)[0]

        self.assertDeleteStatusOK(
            status2del=status2del,
            short_name='quote_status',
            new_status=new_status,
            doc=quote,
        )

    @skipIfCustomAddress
    def test_mass_import_no_total01(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_no_total(user=user, model=Quote, status_model=QuoteStatus)

    def test_mass_import_no_total02(self):
        "Source is managed."
        user = self.login_as_root_and_get()

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

        doc = self._build_csv_doc(lines, user=user)
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

                'user': user.id,
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

    def test_mass_import_total_no_vat_n_vat(self):
        user = self.login_as_root_and_get()
        self._aux_test_csv_import_total_no_vat_n_vat(
            user=user, model=Quote, status_model=QuoteStatus,
        )

    @skipIfCustomAddress
    @skipIfCustomServiceLine
    def test_clone01(self):
        "Organisation not managed => number is set to '0'."
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user=user)

        target.billing_address = b_addr = Address.objects.create(
            name='Billing address 01',
            address='BA1 - Address', city='BA1 - City',
            owner=target,
        )
        target.save()

        # status = QuoteStatus.objects.filter(is_default=False)[0] TODO

        quote = self.create_quote(
            user=user, name='Quote001', source=source, target=target,
            # status=status,
            number='12',
        )
        quote.acceptation_date = date.today()
        quote.save()

        sl = ServiceLine.objects.create(
            related_item=self.create_service(user=user), user=user, related_document=quote,
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
        user = self.login_as_root_and_get()

        source, target = self.create_orgas(user=user)
        self._set_managed(source)

        quote = self.create_quote(user=user, name='My Quote', source=source, target=target)
        self.assertEqual('DE1', quote.number)

        cloned = quote.clone()
        self.assertEqual('DE2', cloned.number)

    def test_num_queries(self):
        """Avoid the queries about line sa creation
        (because these queries can be really slow with a lot of entities)
        """
        from django.db import DEFAULT_DB_ALIAS, connections
        from django.test.utils import CaptureQueriesContext

        user = self.login_as_root_and_get()

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

    def test_brick01(self):
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user=user)

        response1 = self.assertGET200(target.get_absolute_url())
        brick_node1 = self.get_brick_node(
            self.get_html_tree(response1.content),
            brick=ReceivedQuotesBrick,
        )
        self.assertEqual(_('Received quotes'), self.get_brick_title(brick_node1))

        # ---
        quote = Quote.objects.create(
            user=user, name='My Quote',
            status=QuoteStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
        )

        response2 = self.assertGET200(target.get_absolute_url())
        brick_node2 = self.get_brick_node(
            self.get_html_tree(response2.content),
            brick=ReceivedQuotesBrick,
        )
        self.assertBrickTitleEqual(
            brick_node2, count=1,
            title='{count} Received quote', plural_title='{count} Received quotes',
        )
        self.assertListEqual(
            [_('Name'), _('Expiration date'), _('Status'), _('Total without VAT')],
            self.get_brick_table_column_titles(brick_node2),
        )
        rows = self.get_brick_table_rows(brick_node2)
        table_cells = self.get_alone_element(rows).findall('.//td')
        self.assertEqual(4, len(table_cells))
        self.assertInstanceLink(table_cells[0], entity=quote)
        self.assertEqual(
            date_format(quote.expiration_date, 'DATE_FORMAT'),
            table_cells[1].text,
        )
        self.assertEqual(quote.status.name, table_cells[2].text)
        # TODO: test table_cells[3]

    def test_brick02(self):
        "Field 'expiration_date' is hidden."
        user = self.login_as_root_and_get()
        source, target = self.create_orgas(user=user)

        FieldsConfig.objects.create(
            content_type=Quote,
            descriptions=[
                ('expiration_date',  {FieldsConfig.HIDDEN: True}),
            ],
        )

        Quote.objects.create(
            user=user, name='My Quote',
            status=QuoteStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
        )

        response = self.assertGET200(target.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=ReceivedQuotesBrick,
        )
        self.assertListEqual(
            [_('Name'), _('Status'), _('Total without VAT')],
            self.get_brick_table_column_titles(brick_node),
        )
        rows = self.get_brick_table_rows(brick_node)
        row = self.get_alone_element(rows)
        self.assertEqual(3, len(row.findall('.//td')))

    @override_settings(HIDDEN_VALUE='?')
    def test_brick03(self):
        "No VIEW permission."
        user = self.login_as_standard(allowed_apps=['persons', 'billing'])
        # SetCredentials.objects.create(
        #     role=user.role,
        #     value=(
        #         EntityCredentials.VIEW
        #         | EntityCredentials.CHANGE
        #         | EntityCredentials.DELETE
        #         | EntityCredentials.LINK
        #         | EntityCredentials.UNLINK
        #     ),
        #     set_type=SetCredentials.ESET_OWN,
        # )
        self.add_credentials(user.role, own='*')

        source, target = self.create_orgas(user=user)

        Quote.objects.create(
            # user=self.other_user, name='My Quote',
            user=self.get_root_user(), name='My Quote',
            status=QuoteStatus.objects.all()[0],
            source=source, target=target,
            expiration_date=date(year=2023, month=6, day=1),
        )

        response = self.assertGET200(target.get_absolute_url())
        brick_node = self.get_brick_node(
            self.get_html_tree(response.content),
            brick=ReceivedQuotesBrick,
        )
        rows = self.get_brick_table_rows(brick_node)
        row = self.get_alone_element(rows)

        table_cells = row.findall('.//td')
        self.assertEqual(4, len(table_cells))
        self.assertEqual('?', table_cells[0].text)
        self.assertEqual('?', table_cells[1].text)
        self.assertEqual('?', table_cells[2].text)
        self.assertEqual('?', table_cells[3].text)
