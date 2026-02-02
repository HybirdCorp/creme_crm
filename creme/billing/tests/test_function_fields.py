from datetime import date, timedelta
from functools import partial

from django.conf import settings
from django.utils.formats import number_format
from django.utils.translation import gettext as _

from creme.creme_core.core.entity_cell import EntityCellFunctionField
from creme.creme_core.core.function_field import function_field_registry
from creme.creme_core.gui.view_tag import ViewTag
from creme.creme_core.models import FieldsConfig
from creme.persons.tests.base import skipIfCustomOrganisation

from ..function_fields import (
    get_total_pending,
    get_total_won_quote_last_year,
    get_total_won_quote_this_year,
)
from ..models import InvoiceStatus, QuoteStatus
from .base import (
    Invoice,
    Organisation,
    ProductLine,
    Quote,
    TemplateBase,
    _BillingTestCase,
    skipIfCustomInvoice,
    skipIfCustomProductLine,
    skipIfCustomQuote,
)


class _BaseTotalFunctionFieldTestCase(_BillingTestCase):
    def setUp(self):
        super().setUp()
        self.won_status = QuoteStatus.objects.create(name='won_status', won=True)
        self.today_date = date.today()

    def _create_line(self, *, user, entity, unit_price, quantity):
        return ProductLine.objects.create(
            user=user,
            on_the_fly_item='on_the_fly_item',
            related_document=entity,
            unit_price=unit_price,
            quantity=quantity,
        )


@skipIfCustomOrganisation
@skipIfCustomInvoice
@skipIfCustomProductLine
class TotalPendingPaymentTestCase(_BaseTotalFunctionFieldTestCase):
    def setUp(self):
        self.pending_payment_status = InvoiceStatus.objects.create(
            name='pending_payment',
            pending_payment=True,
        )

    def test_main(self):
        user = self.login_as_root_and_get()
        create_orga = partial(Organisation.objects.create, user=user)
        target = create_orga(name='Target')
        self.assertEqual(0, get_total_pending(target, user))

        source1 = create_orga(name='Source#1')
        self._set_managed(source1)

        def set_status(invoice):
            invoice.status = self.pending_payment_status
            invoice.save()

        create_invoice = partial(self.create_invoice, user=user)
        invoice1 = create_invoice(name='Invoice #1', source=source1, target=target)
        set_status(invoice1)

        source2 = create_orga(name='Source#2')
        self._set_managed(source2)

        invoice2 = create_invoice(name='Invoice #2', source=source2, target=target)
        set_status(invoice2)

        # No pending status => not used
        invoice3 = create_invoice(name='Invoice #3', source=source2, target=target)
        self._create_line(user=user, entity=invoice3, unit_price=1000, quantity=1)

        # Not managed source => not used
        source3 = create_orga(name='Source#3 (not managed)')
        invoice4 = create_invoice(name='Invoice #4', source=source3, target=target)
        set_status(invoice4)
        self._create_line(user=user, entity=invoice4, unit_price=500, quantity=1)

        # Other target => not used
        target2 = create_orga(name='Target#2')
        invoice5 = create_invoice(name='Invoice #5', source=source1, target=target2)
        set_status(invoice5)
        self._create_line(user=user, entity=invoice5, unit_price=750, quantity=1)

        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache

        # 2 Queries:
        #  - managed organisations
        #  - only billing issued by managed organisations
        with self.assertNumQueries(2):
            total = get_total_pending(target, user)

        self.assertEqual(0, total)

        self._create_line(user=user, entity=invoice1, unit_price=5000, quantity=1)
        self.assertEqual(5000, get_total_pending(target, user))

        self._create_line(user=user, entity=invoice2, unit_price=2000, quantity=1)
        self.assertEqual(7000, get_total_pending(target, user))

        funf = function_field_registry.get(Organisation, 'total_pending_payment')
        self.assertIsNotNone(funf)

        self.assertEqual(
            number_format('7000.00', force_grouping=True),
            funf(target, user).render(ViewTag.HTML_LIST),
        )
        self.assertEqual(
            number_format('7000.00'),
            funf(target, user).render(ViewTag.TEXT_PLAIN),
        )

        # Test for EntityCellFunctionField + CSS
        cell = EntityCellFunctionField(model=Invoice, func_field=funf)
        self.assertEqual(settings.CSS_NUMBER_LISTVIEW,         cell.listview_css_class)
        self.assertEqual(settings.CSS_DEFAULT_HEADER_LISTVIEW, cell.header_listview_css_class)

    def test_populate(self):
        "populate_entities()."
        user = self.login_as_root_and_get()

        create_orga = partial(Organisation.objects.create, user=user)
        target1 = create_orga(name='Target #1')
        target2 = create_orga(name='Target #2')

        source1 = self._set_managed(create_orga(name='Source#1'))
        source2 = self._set_managed(create_orga(name='Source#2'))

        def set_status(invoice):
            invoice.status = self.pending_payment_status
            invoice.save()

        create_invoice = partial(self.create_invoice, user=user)

        # target1's invoices
        invoice_1_1 = create_invoice(name='Invoice #1-1', source=source1, target=target1)
        set_status(invoice_1_1)
        self._create_line(user=user, entity=invoice_1_1, unit_price=2000, quantity=1)

        invoice_1_2 = create_invoice(name='Invoice #1-2', source=source2, target=target1)
        set_status(invoice_1_2)
        self._create_line(user=user, entity=invoice_1_2, unit_price=1500, quantity=1)

        # No pending status => not used
        invoice_1_3 = create_invoice(name='Invoice #1-3', source=source2, target=target1)
        self._create_line(user=user, entity=invoice_1_3, unit_price=1000, quantity=1)

        # target2's invoices
        invoice_2_1 = create_invoice(name='Invoice #2-1', source=source1, target=target2)
        set_status(invoice_2_1)
        self._create_line(user=user, entity=invoice_2_1, unit_price=3300, quantity=1)

        # Not managed source => not used
        source3 = create_orga(name='Source#3 (not managed)')
        invoice_2_2 = create_invoice(name='Invoice #2-2', source=source3, target=target2)
        set_status(invoice_2_2)
        self._create_line(user=user, entity=invoice_2_2, unit_price=500, quantity=1)

        # Other target => not used
        target3 = create_orga(name='Target#3')
        invoice_3_1 = create_invoice(name='Invoice #5', source=source1, target=target3)
        set_status(invoice_3_1)
        self._create_line(user=user, entity=invoice_3_1, unit_price=750, quantity=1)

        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache

        funf = function_field_registry.get(Organisation, 'total_pending_payment')
        self.assertIsNotNone(funf)

        with self.assertNumQueries(2):
            funf.populate_entities([target1, target2], user)

        with self.assertNumQueries(0):
            total1 = funf(target1, user).render(ViewTag.TEXT_PLAIN)
            total2 = funf(target2, user).render(ViewTag.TEXT_PLAIN)

        self.assertEqual(number_format('3500.00'), total1)
        self.assertEqual(number_format('3300.00'), total2)

    def test_credentials(self):
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice],
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        create_orga = partial(Organisation.objects.create, user=user)
        target = create_orga(name='Target')

        source = create_orga(name='Source#1')
        self._set_managed(source)

        def set_status(invoice):
            invoice.status = self.pending_payment_status
            invoice.save()

        create_invoice = partial(self.create_invoice, user=user)

        invoice1 = create_invoice(name='Invoice #1', source=source, target=target)
        set_status(invoice1)

        invoice2 = create_invoice(name='Invoice #2', source=source, target=target)
        set_status(invoice2)

        # Now viewable => not used
        invoice3 = create_invoice(name='Invoice #3', source=source, target=target)
        set_status(invoice3)

        invoice3.user = self.get_root_user()
        invoice3.save()
        self.assertFalse(user.has_perm_to_view(invoice3))

        self._create_line(user=user, entity=invoice1, unit_price=5000, quantity=1)
        self._create_line(user=user, entity=invoice2, unit_price=2000, quantity=1)
        self._create_line(user=user, entity=invoice3, unit_price=750, quantity=1)  # Not used
        self.assertEqual(7000, get_total_pending(target, user))

    def test_credentials__populate(self):
        user = self.login_as_standard(
            allowed_apps=['persons', 'billing'],
            creatable_models=[Invoice],
        )
        self.add_credentials(user.role, own=['VIEW', 'LINK'])

        create_orga = partial(Organisation.objects.create, user=user)
        target = create_orga(name='Target')

        source = create_orga(name='Source#1')
        self._set_managed(source)

        def set_status(invoice):
            invoice.status = self.pending_payment_status
            invoice.save()

        create_invoice = partial(self.create_invoice, user=user)

        invoice1 = create_invoice(name='Invoice #1', source=source, target=target)
        set_status(invoice1)

        invoice2 = create_invoice(name='Invoice #2', source=source, target=target)
        set_status(invoice2)

        # Now viewable => not used
        invoice3 = create_invoice(name='Invoice #3', source=source, target=target)
        set_status(invoice3)

        invoice3.user = self.get_root_user()
        invoice3.save()
        self.assertFalse(user.has_perm_to_view(invoice3))

        self._create_line(user=user, entity=invoice1, unit_price=3000, quantity=1)
        self._create_line(user=user, entity=invoice2, unit_price=2500, quantity=1)
        self._create_line(user=user, entity=invoice3, unit_price=750, quantity=1)  # Not used

        funf = function_field_registry.get(Organisation, 'total_pending_payment')
        funf.populate_entities([target], user)
        self.assertEqual(number_format('5500.00'), funf(target, user).render(ViewTag.TEXT_PLAIN))

    def test_cache(self):
        "Per-user cache."
        user = self.login_as_root_and_get()
        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Invoice #1')

        invoice.status = self.pending_payment_status
        invoice.save()

        self._set_managed(source)
        self._create_line(user=user, entity=invoice, unit_price=2000, quantity=1)

        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache
        funf = function_field_registry.get(Organisation, 'total_pending_payment')

        with self.assertNumQueries(2):
            total1 = funf(target, user).render(ViewTag.TEXT_PLAIN)

        self.assertEqual(number_format('2000.00'), total1)

        other_user = self.create_user()

        with self.assertNumQueries(2):
            total2 = funf(target, other_user).render(ViewTag.TEXT_PLAIN)

        self.assertEqual(number_format('2000.00'), total2)

        with self.assertNumQueries(0):  # Cache is kept
            funf(target, user).render(ViewTag.TEXT_PLAIN)

    def test_cache__populate(self):
        "Per-user cache + populate()."
        user = self.login_as_root_and_get()
        invoice, source, target = self.create_invoice_n_orgas(user=user, name='Invoice #1')

        invoice.status = self.pending_payment_status
        invoice.save()

        self._set_managed(source)
        self._create_line(user=user, entity=invoice, unit_price=2000, quantity=1)

        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache
        funf = function_field_registry.get(Organisation, 'total_pending_payment')

        with self.assertNumQueries(2):
            funf.populate_entities([target], user)

        with self.assertNumQueries(0):
            total1 = funf(target, user).render(ViewTag.TEXT_PLAIN)

        self.assertEqual(number_format('2000.00'), total1)

        other_user = self.create_user()

        with self.assertNumQueries(2):
            funf.populate_entities([target], other_user)

        with self.assertNumQueries(0):
            total2 = funf(target, other_user).render(ViewTag.TEXT_PLAIN)

        self.assertEqual(number_format('2000.00'), total2)

        with self.assertNumQueries(0):  # Cache is kept
            funf(target, user).render(ViewTag.TEXT_PLAIN)


@skipIfCustomOrganisation
@skipIfCustomQuote
@skipIfCustomProductLine
class TotalWonQuoteLastYearTestCase(_BaseTotalFunctionFieldTestCase):
    def test_main(self):
        user = self.login_as_root_and_get()

        def set_date(quote):
            quote.acceptation_date = self.today_date - timedelta(days=365)
            quote.save()

        quote01, source, target = self.create_quote_n_orgas(
            user=user, name='Quote #1', status=self.won_status,
        )
        set_date(quote01)
        self._set_managed(source)

        quote02 = self.create_quote(
            user=user, name='Quote #2', source=source, target=target, status=self.won_status,
        )
        set_date(quote02)

        # Not won status => not used
        quote03 = self.create_quote(user=user, name='Quote #3', source=source, target=target)
        self.assertFalse(quote03.status.won)
        set_date(quote03)
        self._create_line(user=user, entity=quote03, unit_price=500, quantity=1)

        # Current year => not used
        quote04 = self.create_quote(
            user=user, name='Quote #4', source=source, target=target, status=self.won_status,
        )
        quote04.acceptation_date = self.today_date
        quote04.save()
        self._create_line(user=user, entity=quote04, unit_price=300, quantity=1)

        FieldsConfig.objects.get_for_model(Quote)  # Fill cache
        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache

        with self.assertNumQueries(2):
            total = get_total_won_quote_last_year(target, user)

        self.assertEqual(0, total)

        self._create_line(user=user, entity=quote01, unit_price=5000, quantity=1)
        self._create_line(user=user, entity=quote02, unit_price=300, quantity=1)
        self.assertEqual(5300, get_total_won_quote_last_year(target, user))

        funf = function_field_registry.get(Organisation, 'total_won_quote_last_year')
        self.assertIsNotNone(funf)

        self.assertEqual(
            number_format('5300.00', force_grouping=True),
            funf(target, user).render(ViewTag.HTML_LIST),
        )
        self.assertEqual(
            number_format('5300.00'),
            funf(target, user).render(ViewTag.TEXT_PLAIN),
        )

    def test_hidden_acceptation(self):
        "'acceptation_date' is hidden."
        user = self.login_as_root_and_get()
        quote, source, target = self.create_quote_n_orgas(user=user, name='YOLO')

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

    def test_populate(self):
        "populate_entities()."
        user = self.login_as_root_and_get()
        previous_year = self.today_date - timedelta(days=365)

        def set_date(quote):
            quote.acceptation_date = previous_year
            quote.save()

        quote1, source1, target1 = self.create_quote_n_orgas(
            user=user, name='Quote01', status=self.won_status,
        )
        quote2, source2, target2 = self.create_quote_n_orgas(
            user=user, name='Quote02', status=self.won_status,
        )

        # Not won status => not used
        quote3 = self.create_quote(user=user, name='Quote #3', source=source1, target=target1)
        self.assertFalse(quote3.status.won)

        # Current year => not used
        quote4 = self.create_quote(
            user=user, name='Quote #4', source=source1, target=target2, status=self.won_status,
        )
        quote4.acceptation_date = self.today_date
        quote4.save()

        set_date(quote1)
        set_date(quote2)
        set_date(quote3)

        self._set_managed(source1)
        self._set_managed(source2)

        self._create_line(user=user, entity=quote1, unit_price=5000, quantity=1)
        self._create_line(user=user, entity=quote2, unit_price=4000, quantity=1)
        self._create_line(user=user, entity=quote3, unit_price=500, quantity=1)  # Not used
        self._create_line(user=user, entity=quote4, unit_price=300, quantity=1)   # Not used

        funf = function_field_registry.get(Organisation, 'total_won_quote_last_year')
        self.assertIsNotNone(funf)

        FieldsConfig.objects.get_for_model(Quote)  # Fill cache
        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache

        with self.assertNumQueries(2):
            funf.populate_entities([target1, target2], user)

        with self.assertNumQueries(0):
            total1 = funf(target1, user).render(ViewTag.TEXT_PLAIN)
            total2 = funf(target2, user).render(ViewTag.TEXT_PLAIN)

        self.assertEqual(number_format('5000.00'), total1)
        self.assertEqual(number_format('4000.00'), total2)

    def test_hidden_acceptation__populate(self):
        "'acceptation_date' is hidden + populate_entities()."
        user = self.login_as_root_and_get()
        quote1, source1, target1 = self.create_quote_n_orgas(user=user, name='Quote1')
        quote2, source2, target2 = self.create_quote_n_orgas(user=user, name='Quote2')

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


@skipIfCustomOrganisation
@skipIfCustomQuote
@skipIfCustomProductLine
class TotalWonQuoteThisYearTestCase(_BaseTotalFunctionFieldTestCase):
    def test_main(self):
        user = self.login_as_root_and_get()

        def set_date(quote):
            quote.acceptation_date = self.today_date
            quote.save()

        quote01, source, target = self.create_quote_n_orgas(
            user=user, name='Quote #1', status=self.won_status,
        )
        set_date(quote01)
        self._set_managed(source)

        quote02 = self.create_quote(
            user=user, name='Quote #2', source=source, target=target, status=self.won_status,
        )
        set_date(quote02)

        # Not won status => not used
        quote03 = self.create_quote(user=user, name='Quote #3', source=source, target=target)
        self.assertFalse(quote03.status.won)
        set_date(quote03)
        self._create_line(user=user, entity=quote03, unit_price=500, quantity=1)

        # Previous year => not used
        quote04 = self.create_quote(
            user=user, name='Quote #4', source=source, target=target, status=self.won_status,
        )
        quote04.acceptation_date = self.today_date - timedelta(days=366)
        quote04.save()
        self._create_line(user=user, entity=quote04, unit_price=300, quantity=1)

        FieldsConfig.objects.get_for_model(Quote)  # Fill cache
        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache

        with self.assertNumQueries(2):
            total = get_total_won_quote_this_year(target, user)

        self.assertEqual(0, total)

        self._create_line(user=user, entity=quote01, unit_price=5000, quantity=1)
        self._create_line(user=user, entity=quote02, unit_price=1000, quantity=1)
        self.assertEqual(6000, get_total_won_quote_this_year(target, user))

        funf = function_field_registry.get(Organisation, 'total_won_quote_this_year')
        self.assertIsNotNone(funf)

        self.assertEqual(
            number_format('6000.00', force_grouping=True),
            funf(target, user).render(ViewTag.HTML_LIST),
        )
        self.assertEqual(
            number_format('6000.00'),
            funf(target, user).render(ViewTag.TEXT_PLAIN),
        )

    def test_populate(self):
        "'populate_entities()."
        user = self.login_as_root_and_get()

        def set_date(quote):
            quote.acceptation_date = self.today_date
            quote.save()

        create_quote_n_orgas = self.create_quote_n_orgas
        quote01, source01, target01 = create_quote_n_orgas(
            user=user, name='Quote #1', status=self.won_status,
        )
        quote02, source02, target02 = create_quote_n_orgas(
            user=user, name='Quote #2', status=self.won_status,
        )

        # Not won status => not used
        quote03 = self.create_quote(user=user, name='Quote #3', source=source01, target=target01)
        self.assertFalse(quote03.status.won)

        set_date(quote01)
        set_date(quote02)
        set_date(quote03)

        # Previous year => not used
        quote04 = self.create_quote(
            user=user, name='Quote #4', source=source01, target=target01, status=self.won_status,
        )
        quote04.acceptation_date = self.today_date - timedelta(days=366)
        quote04.save()

        self._set_managed(source01)
        self._set_managed(source02)

        self._create_line(user=user, entity=quote01, unit_price=5000, quantity=1)
        self._create_line(user=user, entity=quote02, unit_price=2500, quantity=1)
        self._create_line(user=user, entity=quote03, unit_price=1000, quantity=1)  # Not used
        self._create_line(user=user, entity=quote04, unit_price=300, quantity=1)  # Not used

        funf = function_field_registry.get(Organisation, 'total_won_quote_this_year')
        self.assertIsNotNone(funf)

        FieldsConfig.objects.get_for_model(Quote)  # Fill cache
        bool(Organisation.objects.filter_managed_by_creme())  # Fill cache

        with self.assertNumQueries(2):
            funf.populate_entities([target01, target02], user)

        with self.assertNumQueries(0):
            total1 = funf(target01, user).render(ViewTag.TEXT_PLAIN)
            total2 = funf(target02, user).render(ViewTag.TEXT_PLAIN)

        self.assertEqual(number_format('5000.00'), total1)
        self.assertEqual(number_format('2500.00'), total2)

    def test_hidden_acceptation(self):
        "'acceptation_date' is hidden."
        user = self.login_as_root_and_get()

        quote, source, target = self.create_quote_n_orgas(user=user, name='Quote #1')
        FieldsConfig.objects.create(
            content_type=Quote,
            descriptions=[('acceptation_date', {FieldsConfig.HIDDEN: True})],
        )

        funf = function_field_registry.get(Organisation, 'total_won_quote_this_year')

        FieldsConfig.objects.get_for_model(Quote)  # Fill cache

        with self.assertNumQueries(0):
            total = funf(target, user).render(ViewTag.TEXT_PLAIN)

        self.assertEqual(_('Error: «Acceptation date» is hidden'), total)

    def test_hidden_acceptation__populate(self):
        "'acceptation_date' is hidden + populate_entities()."
        user = self.login_as_root_and_get()
        quote1, source1, target1 = self.create_quote_n_orgas(user=user, name='Quote1')
        quote2, source2, target2 = self.create_quote_n_orgas(user=user, name='Quote2')

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


class TemplateBaseVerboseStatusFieldTestCase(_BillingTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = user = cls.get_root_user()

        create_orga = partial(Organisation.objects.create, user=user)
        cls.source = create_orga(name='Source')
        cls.target = create_orga(name='Target')

    def _create_templatebase(self, model, status_uuid, name=None, comment='', **kwargs):
        return TemplateBase.objects.create(
            user=self.user,
            ct=model,
            name=name or f'{model._meta.verbose_name} template',
            status_uuid=status_uuid,
            comment=comment,
            source=self.source,
            target=self.target,
            **kwargs
        )

    def test_main(self):
        status = InvoiceStatus.objects.filter(is_default=False).first()
        tpl = self._create_templatebase(Invoice, status_uuid=status.uuid)

        with self.assertNoException():
            funf = function_field_registry.get(TemplateBase, 'get_verbose_status')

        self.assertIsNotNone(funf)

        # ---
        with self.assertNumQueries(1):
            render1 = funf(tpl, self.user).render(ViewTag.TEXT_PLAIN)

        self.assertEqual(str(status), render1)

        # ---
        with self.assertNumQueries(0):
            render2 = funf(tpl, self.user).render(ViewTag.HTML_LIST)

        self.assertHTMLEqual(
            f'<div class="ui-creme-colored_status">'
            f' <div class="ui-creme-color_indicator" style="background-color:#{status.color};" />'
            f' <span>{status.name}</span>'
            f'</div>',
            render2,
        )

        # ---
        with self.assertNumQueries(0):
            render3 = funf(tpl, self.user).render(ViewTag.HTML_LIST)

        self.assertEqual(render2, render3)

    def test_populate(self):
        user = self.user

        status1, status2 = InvoiceStatus.objects.filter(is_default=False)[:2]
        tpl1 = self._create_templatebase(Invoice, status_uuid=status1.uuid)
        tpl2 = self._create_templatebase(Invoice, status_uuid=status2.uuid)

        funf = function_field_registry.get(TemplateBase, 'get_verbose_status')

        with self.assertNumQueries(1):
            funf.populate_entities(entities=[tpl1, tpl2], user=user)

        with self.assertNumQueries(0):
            render1 = funf(tpl1, user).render(ViewTag.TEXT_PLAIN)
        self.assertEqual(str(status1), render1)

        with self.assertNumQueries(0):
            render2 = funf(tpl2, user).render(ViewTag.TEXT_PLAIN)
        self.assertEqual(str(status2), render2)

        # Status already retrieved
        tpl3 = self._create_templatebase(Invoice, status_uuid=status2.uuid)
        with self.assertNumQueries(0):
            funf.populate_entities(entities=[tpl1, tpl2, tpl3], user=user)

        with self.assertNumQueries(0):
            render3 = funf(tpl3, user).render(ViewTag.TEXT_PLAIN)
        self.assertEqual(str(status2), render3)

    def test_populate_several_models(self):
        user = self.user

        status1 = InvoiceStatus.objects.filter(is_default=False).first()
        status2 = QuoteStatus.objects.filter(is_default=False).first()
        tpl1 = self._create_templatebase(Invoice, status_uuid=status1.uuid)
        tpl2 = self._create_templatebase(Quote, status_uuid=status2.uuid)

        funf = function_field_registry.get(TemplateBase, 'get_verbose_status')

        with self.assertNumQueries(2):
            funf.populate_entities(entities=[tpl1, tpl2], user=user)

        with self.assertNumQueries(0):
            render1 = funf(tpl1, user).render(ViewTag.TEXT_PLAIN)
        self.assertEqual(str(status1), render1)

        with self.assertNumQueries(0):
            render2 = funf(tpl2, user).render(ViewTag.TEXT_PLAIN)
        self.assertEqual(str(status2), render2)
