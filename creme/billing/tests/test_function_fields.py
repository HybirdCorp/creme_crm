# -*- coding: utf-8 -*-

from datetime import date, timedelta
from functools import partial

from django.conf import settings
from django.utils.formats import number_format
from django.utils.translation import gettext as _

from creme.creme_core.auth.entity_credentials import EntityCredentials
from creme.creme_core.core.entity_cell import EntityCellFunctionField
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.models import FieldsConfig, SetCredentials
from creme.persons.tests.base import skipIfCustomOrganisation

from ..function_fields import (
    get_total_pending,
    get_total_won_quote_last_year,
    get_total_won_quote_this_year,
)
from ..models import InvoiceStatus, QuoteStatus
from .base import (
    Contact,
    Invoice,
    Organisation,
    ProductLine,
    Quote,
    _BillingTestCase,
    skipIfCustomInvoice,
    skipIfCustomProductLine,
    skipIfCustomQuote,
)


@skipIfCustomOrganisation
class FunctionFieldTestCase(_BillingTestCase):
    def setUp(self):
        super().setUp()
        self.won_status = QuoteStatus.objects.create(name='won_status', won=True)
        self.pending_payment_status = InvoiceStatus.objects.create(
            name='pending_payment',
            pending_payment=True,
        )
        self.today_date = date.today()

    def create_line(self, related_document, unit_price, quantity):
        return ProductLine.objects.create(
            user=self.user,
            on_the_fly_item='on_the_fly_item',
            related_document=related_document,
            unit_price=unit_price,
            quantity=quantity,
        )

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_get_total_pending01(self):
        user = self.login()
        create_orga = partial(Organisation.objects.create, user=user)
        target = create_orga(name='Target')
        self.assertEqual(0, get_total_pending(target, user))

        source01 = create_orga(name='Source#1')
        self._set_managed(source01)

        def set_status(invoice):
            invoice.status = self.pending_payment_status
            invoice.save()

        invoice01 = self.create_invoice('Invoice #1', source01, target, user=user)
        set_status(invoice01)

        source02 = create_orga(name='Source#2')
        self._set_managed(source02)

        invoice02 = self.create_invoice('Invoice #2', source02, target, user=user)
        set_status(invoice02)

        # No pending status => not used
        invoice03 = self.create_invoice('Invoice #3', source02, target, user=user)
        self.create_line(invoice03, 1000, 1)

        # Not managed source => not used
        source03 = create_orga(name='Source#3 (not managed)')
        invoice04 = self.create_invoice('Invoice #4', source03, target, user=user)
        set_status(invoice04)
        self.create_line(invoice04, 500, 1)

        # Other target => not used
        target02 = create_orga(name='Target#2')
        invoice05 = self.create_invoice('Invoice #5', source01, target02, user=user)
        set_status(invoice05)
        self.create_line(invoice05, 750, 1)

        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache

        # 2 Queries:
        #  - managed organisations
        #  - only billing issued by managed organisations
        with self.assertNumQueries(2):
            total = get_total_pending(target, user)

        self.assertEqual(0, total)

        self.create_line(invoice01, 5000, 1)
        self.assertEqual(5000, get_total_pending(target, user))

        self.create_line(invoice02, 2000, 1)
        self.assertEqual(7000, get_total_pending(target, user))

        funf = function_field_registry.get(Organisation, 'total_pending_payment')
        self.assertIsNotNone(funf)

        self.assertEqual(
            number_format('7000.00', use_l10n=True, force_grouping=True),
            funf(target, user).for_html()
        )
        self.assertEqual(
            number_format('7000.00', use_l10n=True),
            funf(target, user).for_csv()
        )

        # Test for EntityCellFunctionField + CSS
        cell = EntityCellFunctionField(model=Invoice, func_field=funf)
        self.assertEqual(settings.CSS_NUMBER_LISTVIEW,         cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_get_total_pending02(self):
        "populate_entities()."
        user = self.login()

        create_orga = partial(Organisation.objects.create, user=user)
        target01 = create_orga(name='Target #1')
        target02 = create_orga(name='Target #2')

        source01 = self._set_managed(create_orga(name='Source#1'))
        source02 = self._set_managed(create_orga(name='Source#2'))

        def set_status(invoice):
            invoice.status = self.pending_payment_status
            invoice.save()

        # target01's invoices
        invoice_1_1 = self.create_invoice('Invoice #1-1', source01, target01, user=user)
        set_status(invoice_1_1)
        self.create_line(invoice_1_1, 2000, 1)

        invoice_1_2 = self.create_invoice('Invoice #1-2', source02, target01, user=user)
        set_status(invoice_1_2)
        self.create_line(invoice_1_2, 1500, 1)

        # No pending status => not used
        invoice_1_3 = self.create_invoice('Invoice #1-3', source02, target01, user=user)
        self.create_line(invoice_1_3, 1000, 1)

        # target02's invoices
        invoice_2_1 = self.create_invoice('Invoice #2-1', source01, target02, user=user)
        set_status(invoice_2_1)
        self.create_line(invoice_2_1, 3300, 1)

        # Not managed source => not used
        source03 = create_orga(name='Source#3 (not managed)')
        invoice_2_2 = self.create_invoice('Invoice #2-2', source03, target02, user=user)
        set_status(invoice_2_2)
        self.create_line(invoice_2_2, 500, 1)

        # Other target => not used
        target03 = create_orga(name='Target#3')
        invoice_3_1 = self.create_invoice('Invoice #5', source01, target03, user=user)
        set_status(invoice_3_1)
        self.create_line(invoice_3_1, 750, 1)

        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache

        funf = function_field_registry.get(Organisation, 'total_pending_payment')
        self.assertIsNotNone(funf)

        with self.assertNumQueries(2):
            funf.populate_entities([target01, target02], user)

        with self.assertNumQueries(0):
            total1 = funf(target01, user).for_csv()
            total2 = funf(target02, user).for_csv()

        self.assertEqual(number_format('3500.00', use_l10n=True), total1)
        self.assertEqual(number_format('3300.00', use_l10n=True), total2)

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_get_total_pending03(self):
        "Credentials."
        user = self.login(
            is_superuser=False,
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice],
        )

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_OWN,
        )

        create_orga = partial(Organisation.objects.create, user=user)
        target = create_orga(name='Target')

        source01 = create_orga(name='Source#1')
        self._set_managed(source01)

        def set_status(invoice):
            invoice.status = self.pending_payment_status
            invoice.save()

        invoice01 = self.create_invoice('Invoice #1', source01, target, user=user)
        set_status(invoice01)

        invoice02 = self.create_invoice('Invoice #2', source01, target, user=user)
        set_status(invoice02)

        # Now viewable => not used
        invoice03 = self.create_invoice('Invoice #3', source01, target, user=user)
        set_status(invoice03)

        invoice03.user = self.other_user
        invoice03.save()
        self.assertFalse(user.has_perm_to_view(invoice03))

        self.create_line(invoice01, 5000, 1)
        self.create_line(invoice02, 2000, 1)
        self.create_line(invoice03, 750, 1)  # Not used
        self.assertEqual(7000, get_total_pending(target, user))

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_get_total_pending04(self):
        "Credentials + populate()."
        user = self.login(
            is_superuser=False,
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice],
        )

        SetCredentials.objects.create(
            role=self.role,
            value=EntityCredentials.VIEW | EntityCredentials.LINK,
            set_type=SetCredentials.ESET_OWN,
        )

        create_orga = partial(Organisation.objects.create, user=user)
        target = create_orga(name='Target')

        source01 = create_orga(name='Source#1')
        self._set_managed(source01)

        def set_status(invoice):
            invoice.status = self.pending_payment_status
            invoice.save()

        invoice01 = self.create_invoice('Invoice #1', source01, target, user=user)
        set_status(invoice01)

        invoice02 = self.create_invoice('Invoice #2', source01, target, user=user)
        set_status(invoice02)

        # Now viewable => not used
        invoice03 = self.create_invoice('Invoice #3', source01, target, user=user)
        set_status(invoice03)

        invoice03.user = self.other_user
        invoice03.save()
        self.assertFalse(user.has_perm_to_view(invoice03))

        self.create_line(invoice01, 3000, 1)
        self.create_line(invoice02, 2500, 1)
        self.create_line(invoice03, 750, 1)  # Not used

        funf = function_field_registry.get(Organisation, 'total_pending_payment')
        funf.populate_entities([target], user)
        self.assertEqual(number_format('5500.00', use_l10n=True), funf(target, user).for_csv())

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_get_total_pending05(self):
        "Per-user cache."
        user = self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice #1', user=user)

        invoice.status = self.pending_payment_status
        invoice.save()

        self._set_managed(source)
        self.create_line(invoice, 2000, 1)

        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache
        funf = function_field_registry.get(Organisation, 'total_pending_payment')

        with self.assertNumQueries(2):
            total1 = funf(target, user).for_csv()

        self.assertEqual(number_format('2000.00', use_l10n=True), total1)

        other_user = self.other_user
        other_user.is_superuser = True
        other_user.role = None
        other_user.save()

        with self.assertNumQueries(2):
            total2 = funf(target, other_user).for_csv()

        self.assertEqual(number_format('2000.00', use_l10n=True), total2)

        with self.assertNumQueries(0):  # Cache is kept
            funf(target, user).for_csv()

    @skipIfCustomInvoice
    @skipIfCustomProductLine
    def test_get_total_pending06(self):
        "Per-user cache + populate()."
        user = self.login()
        invoice, source, target = self.create_invoice_n_orgas('Invoice #1', user=user)

        invoice.status = self.pending_payment_status
        invoice.save()

        self._set_managed(source)
        self.create_line(invoice, 2000, 1)

        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache
        funf = function_field_registry.get(Organisation, 'total_pending_payment')

        with self.assertNumQueries(2):
            funf.populate_entities([target], user)

        with self.assertNumQueries(0):
            total1 = funf(target, user).for_csv()

        self.assertEqual(number_format('2000.00', use_l10n=True), total1)

        other_user = self.other_user
        other_user.is_superuser = True
        other_user.role = None
        other_user.save()

        with self.assertNumQueries(2):
            funf.populate_entities([target], other_user)

        with self.assertNumQueries(0):
            total2 = funf(target, other_user).for_csv()

        self.assertEqual(number_format('2000.00', use_l10n=True), total2)

        with self.assertNumQueries(0):  # Cache is kept
            funf(target, user).for_csv()

    @skipIfCustomQuote
    @skipIfCustomProductLine
    def test_get_total_won_quote_last_year01(self):
        user = self.login()

        def set_date(quote):
            quote.acceptation_date = self.today_date - timedelta(days=365)
            quote.save()

        quote01, source, target = self.create_quote_n_orgas('Quote #1', status=self.won_status)
        set_date(quote01)
        self._set_managed(source)

        quote02 = self.create_quote('Quote #2', source, target, status=self.won_status)
        set_date(quote02)

        # Not won status => not used
        quote03 = self.create_quote('Quote #3', source, target)
        self.assertFalse(quote03.status.won)
        set_date(quote03)
        self.create_line(quote03, 500, 1)

        # Current year => not used
        quote04 = self.create_quote('Quote #4', source, target, status=self.won_status)
        quote04.acceptation_date = self.today_date
        quote04.save()
        self.create_line(quote04, 300, 1)

        FieldsConfig.objects.get_for_model(Quote)  # Fill cache
        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache

        with self.assertNumQueries(2):
            total = get_total_won_quote_last_year(target, user)

        self.assertEqual(0, total)

        self.create_line(quote01, 5000, 1)
        self.create_line(quote02, 300, 1)
        self.assertEqual(5300, get_total_won_quote_last_year(target, user))

        funf = function_field_registry.get(Organisation, 'total_won_quote_last_year')
        self.assertIsNotNone(funf)

        self.assertEqual(
            number_format('5300.00', use_l10n=True, force_grouping=True),
            funf(target, user).for_html(),
        )
        self.assertEqual(
            number_format('5300.00', use_l10n=True),
            funf(target, user).for_csv(),
        )

    @skipIfCustomQuote
    @skipIfCustomProductLine
    def test_get_total_won_quote_last_year02(self):
        "'acceptation_date' is hidden."
        user = self.login()
        quote, source, target = self.create_quote_n_orgas('YOLO')

        FieldsConfig.objects.create(
            content_type=Quote,
            descriptions=[('acceptation_date', {FieldsConfig.HIDDEN: True})],
        )

        quote.acceptation_date = self.today_date
        self._set_managed(source)

        FieldsConfig.objects.get_for_model(Quote)  # Fill cache

        with self.assertNumQueries(0):
            total = get_total_won_quote_last_year(target, user)

        self.assertEqual(_('Error: «Acceptation date» is hidden'), total)

    @skipIfCustomQuote
    @skipIfCustomProductLine
    def test_get_total_won_quote_last_year03(self):
        "'populate_entities()."
        user = self.login()
        previous_year = self.today_date - timedelta(days=365)

        def set_date(quote):
            quote.acceptation_date = previous_year
            quote.save()

        quote01, source01, target01 = self.create_quote_n_orgas('Quote01', status=self.won_status)
        quote02, source02, target02 = self.create_quote_n_orgas('Quote02', status=self.won_status)

        # Not won status => not used
        quote03 = self.create_quote('Quote #3', source01, target01)
        self.assertFalse(quote03.status.won)

        # Current year => not used
        quote04 = self.create_quote('Quote #4', source01, target02, status=self.won_status)
        quote04.acceptation_date = self.today_date
        quote04.save()

        set_date(quote01)
        set_date(quote02)
        set_date(quote03)

        self._set_managed(source01)
        self._set_managed(source02)

        self.create_line(quote01, 5000, 1)
        self.create_line(quote02, 4000, 1)
        self.create_line(quote03, 500,  1)  # Not used
        self.create_line(quote04, 300, 1)   # Not used

        funf = function_field_registry.get(Organisation, 'total_won_quote_last_year')
        self.assertIsNotNone(funf)

        FieldsConfig.objects.get_for_model(Quote)  # Fill cache
        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache

        with self.assertNumQueries(2):
            funf.populate_entities([target01, target02], user)

        with self.assertNumQueries(0):
            total1 = funf(target01, user).for_csv()
            total2 = funf(target02, user).for_csv()

        self.assertEqual(number_format('5000.00', use_l10n=True), total1)
        self.assertEqual(number_format('4000.00', use_l10n=True), total2)

    @skipIfCustomQuote
    @skipIfCustomProductLine
    def test_get_total_won_quote_last_year04(self):
        "'acceptation_date' is hidden + populate_entities()."
        user = self.login()
        quote1, source1, target1 = self.create_quote_n_orgas('Quote1')
        quote2, source2, target2 = self.create_quote_n_orgas('Quote2')

        FieldsConfig.objects.create(
            content_type=Quote,
            descriptions=[('acceptation_date', {FieldsConfig.HIDDEN: True})]
        )

        funf = function_field_registry.get(Organisation, 'total_won_quote_last_year')

        FieldsConfig.objects.get_for_model(Quote)  # Fill cache

        with self.assertNumQueries(0):
            funf.populate_entities([target1, target2], user)

        with self.assertNumQueries(0):
            total1 = get_total_won_quote_last_year(target1, user)
            total2 = get_total_won_quote_last_year(target2, user)

        msg = _('Error: «Acceptation date» is hidden')
        self.assertEqual(msg, total1)
        self.assertEqual(msg, total2)

    @skipIfCustomQuote
    @skipIfCustomProductLine
    def test_get_total_won_quote_this_year01(self):
        user = self.login()

        def set_date(quote):
            quote.acceptation_date = self.today_date
            quote.save()

        quote01, source, target = self.create_quote_n_orgas('Quote #1', status=self.won_status)
        set_date(quote01)
        self._set_managed(source)

        quote02 = self.create_quote('Quote #2', source, target, status=self.won_status)
        set_date(quote02)

        # Not won status => not used
        quote03 = self.create_quote('Quote #3', source, target)
        self.assertFalse(quote03.status.won)
        set_date(quote03)
        self.create_line(quote03, 500, 1)

        # Previous year => not used
        quote04 = self.create_quote('Quote #4', source, target, status=self.won_status)
        quote04.acceptation_date = self.today_date - timedelta(days=366)
        quote04.save()
        self.create_line(quote04, 300, 1)

        FieldsConfig.objects.get_for_model(Quote)  # Fill cache
        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache

        with self.assertNumQueries(2):
            total = get_total_won_quote_this_year(target, user)

        self.assertEqual(0, total)

        self.create_line(quote01, 5000, 1)
        self.create_line(quote02, 1000, 1)
        self.assertEqual(6000, get_total_won_quote_this_year(target, user))

        funf = function_field_registry.get(Organisation, 'total_won_quote_this_year')
        self.assertIsNotNone(funf)

        self.assertEqual(
            number_format('6000.00', use_l10n=True, force_grouping=True),
            funf(target, user).for_html(),
        )
        self.assertEqual(
            number_format('6000.00', use_l10n=True),
            funf(target, user).for_csv(),
        )

    @skipIfCustomQuote
    @skipIfCustomProductLine
    def test_get_total_won_quote_this_year02(self):
        "'acceptation_date' is hidden."
        user = self.login()

        quote, source, target = self.create_quote_n_orgas('Quote #1')
        FieldsConfig.objects.create(
            content_type=Quote,
            descriptions=[('acceptation_date', {FieldsConfig.HIDDEN: True})],
        )

        funf = function_field_registry.get(Organisation, 'total_won_quote_this_year')

        FieldsConfig.objects.get_for_model(Quote)  # Fill cache

        with self.assertNumQueries(0):
            total = funf(target, user).for_csv()

        self.assertEqual(_('Error: «Acceptation date» is hidden'), total)

    @skipIfCustomQuote
    @skipIfCustomProductLine
    def test_get_total_won_quote_this_year03(self):
        "'populate_entities()."
        user = self.login()

        def set_date(quote):
            quote.acceptation_date = self.today_date
            quote.save()

        create_quote_n_orgas = self.create_quote_n_orgas
        quote01, source01, target01 = create_quote_n_orgas('Quote #1', status=self.won_status)
        quote02, source02, target02 = create_quote_n_orgas('Quote #2', status=self.won_status)

        # Not won status => not used
        quote03 = self.create_quote('Quote #3', source01, target01)
        self.assertFalse(quote03.status.won)

        set_date(quote01)
        set_date(quote02)
        set_date(quote03)

        # Previous year => not used
        quote04 = self.create_quote('Quote #4', source01, target01, status=self.won_status)
        quote04.acceptation_date = self.today_date - timedelta(days=366)
        quote04.save()

        self._set_managed(source01)
        self._set_managed(source02)

        self.create_line(quote01, 5000, 1)
        self.create_line(quote02, 2500, 1)
        self.create_line(quote03, 1000, 1)  # Not used
        self.create_line(quote04, 300, 1)  # Not used

        funf = function_field_registry.get(Organisation, 'total_won_quote_this_year')
        self.assertIsNotNone(funf)

        FieldsConfig.objects.get_for_model(Quote)  # Fill cache
        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache

        with self.assertNumQueries(2):
            funf.populate_entities([target01, target02], user)

        with self.assertNumQueries(0):
            total1 = funf(target01, user).for_csv()
            total2 = funf(target02, user).for_csv()

        self.assertEqual(number_format('5000.00', use_l10n=True), total1)
        self.assertEqual(number_format('2500.00', use_l10n=True), total2)

    @skipIfCustomQuote
    @skipIfCustomProductLine
    def test_get_total_won_quote_this_year04(self):
        "'acceptation_date' is hidden + populate_entities()."
        user = self.login()
        quote1, source1, target1 = self.create_quote_n_orgas('Quote1')
        quote2, source2, target2 = self.create_quote_n_orgas('Quote2')

        FieldsConfig.objects.create(
            content_type=Quote,
            descriptions=[('acceptation_date', {FieldsConfig.HIDDEN: True})],
        )

        funf = function_field_registry.get(Organisation, 'total_won_quote_this_year')

        FieldsConfig.objects.get_for_model(Quote)  # Fill cache

        with self.assertNumQueries(0):
            funf.populate_entities([target1, target2], user)

        with self.assertNumQueries(0):
            total1 = get_total_won_quote_this_year(target1, user)
            total2 = get_total_won_quote_this_year(target2, user)

        msg = _('Error: «Acceptation date» is hidden')
        self.assertEqual(msg, total1)
        self.assertEqual(msg, total2)

    @skipIfCustomQuote
    def test_functionfields(self):
        user = self.login()
        quote, source, target = self.create_quote_n_orgas('YOLO')

        for model in (Organisation, Contact):
            for name in (
                'total_pending_payment',
                'total_won_quote_this_year',
                'total_won_quote_last_year',
            ):
                funf = function_field_registry.get(model, name)
                self.assertIsNotNone(funf, f'Function field {model}/{name} is None?!')
                self.assertEqual('0', funf(target, user).for_html())
